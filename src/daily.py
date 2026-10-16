"""Punto de entrada de la extracción diaria de cuestionarios MediCloud."""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta

from dotenv import load_dotenv

from src.audit import (
    NO_HASH,
    AuditError,
    batch_hash,
    is_processed,
    new_load_id,
    pending_days,
    persist_day,
    record_failure,
)
from src.auth import MedicloudAuthError, get_access_token
from src.client import MedicloudAPIError, get_cuestionarios
from src.config import load_settings
from src.dates import previous_day
from src.schema import compare_schema, load_reference
from src.storage import StorageError
from src.validation import validate_questionnaires


class JsonFormatter(logging.Formatter):
    """Formatea los eventos de ejecución como registros JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger(__name__)
_json_handler = logging.StreamHandler(sys.stderr)
_json_handler.setFormatter(JsonFormatter())

MAX_RECOVERY_DAYS = 7


def configure_logging() -> None:
    """Instala el formateador JSON una sola vez."""
    logger.setLevel(logging.INFO)
    if _json_handler not in logger.handlers:
        logger.addHandler(_json_handler)


def parse_iso_date(value: str) -> date:
    """Acepta únicamente fechas ISO completas, YYYY-MM-DD."""
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "La fecha debe tener formato YYYY-MM-DD"
        ) from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError(
            "La fecha debe tener formato YYYY-MM-DD"
        )
    return parsed


def main(dry_run: bool = False, *, target_date: date | None = None) -> int:
    """Extrae y valida; en modo normal confirma carga y auditoría juntas."""
    configure_logging()

    started_at = datetime.now(UTC)
    load_id = new_load_id()
    fecha = None
    database_url = None
    rows_read = 0
    source_hash = NO_HASH
    category = "CONFIG_ERROR"

    try:
        settings = load_settings()
        last_complete_day = previous_day()
        if target_date is not None and target_date > last_complete_day:
            raise ValueError("La fecha solicitada no está completada")
        fecha = target_date if target_date is not None else last_complete_day

        if not dry_run:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL no configurada")
            category = "AUDIT_ERROR"
            if is_processed(database_url, fecha):
                logger.info("Fecha ya procesada. Fecha: %s", fecha)
                return 0

        logger.info("Inicio de extracción diaria. Fecha: %s", fecha)

        category = "AUTH_ERROR"
        token = get_access_token(settings)
        category = "API_ERROR"
        cuestionarios = get_cuestionarios(
            settings=settings,
            token=token,
            fecha_inicial=fecha,
            fecha_final=fecha,
        )
        rows_read = len(cuestionarios)

        category = "VALIDATION_ERROR"
        validate_questionnaires(cuestionarios, fecha, fecha)
        category = "SCHEMA_ERROR"
        report = compare_schema(cuestionarios, load_reference())
        if report.changed:
            logger.warning(
                "Cambio de esquema detectado: campos_nuevos=%d "
                "campos_ausentes=%d registros_inconsistentes=%d",
                len(report.new_fields),
                len(report.missing_fields),
                report.inconsistent_records,
            )

        if dry_run:
            logger.info(
                "Simulación completada sin persistencia. Fecha: %s. Registros: %d",
                fecha,
                rows_read,
            )
            return 0

        category = "STORAGE_ERROR"
        source_hash = batch_hash(cuestionarios)
        result = persist_day(
            database_url, fecha, cuestionarios, started_at, load_id
        )
        if result.already_processed:
            logger.info("Fecha procesada por otra ejecución. Fecha: %s", fecha)
        else:
            logger.info(
                "Persistencia y auditoría confirmadas. Fecha: %s. "
                "Recibidos: %d. Nuevos: %d",
                fecha,
                rows_read,
                result.inserted,
            )
        return 0

    except (
        ValueError,
        MedicloudAuthError,
        MedicloudAPIError,
        StorageError,
        AuditError,
    ) as exc:
        if isinstance(exc, AuditError):
            category = "AUDIT_ERROR"

        if not dry_run and database_url and fecha is not None:
            try:
                record_failure(
                    database_url, fecha, started_at, load_id,
                    category, rows_read, source_hash,
                )
            except AuditError:
                logger.error("No fue posible registrar el fallo en auditoría.")

        logger.error("La extracción diaria ha fallado.")
        return 1

def run_date_range(
    start_date: date, end_date: date, *, dry_run: bool = False
) -> int:
    """Procesa días consecutivos con auditoría y transacción por fecha.

    Ante un fallo, conserva los éxitos anteriores y detiene el intervalo.
    """
    configure_logging()
    if start_date > end_date:
        logger.error("Intervalo inválido: la fecha inicial supera la final.")
        return 1
    if end_date > previous_day():
        logger.error("Intervalo inválido: contiene fechas no completadas.")
        return 1

    for offset in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=offset)
        if main(dry_run=dry_run, target_date=day) != 0:
            logger.error("Intervalo detenido por fallo en la fecha: %s", day)
            return 1
    return 0


def run_recovery() -> int:
    """Recupera hasta siete días pendientes, nunca anteriores a configuración."""
    configure_logging()
    load_dotenv()
    raw_start = os.getenv("CLISUENO_START_DATE")
    if not raw_start:
        logger.error("CLISUENO_START_DATE es obligatorio para --recover.")
        return 1

    try:
        first_day = parse_iso_date(raw_start)
    except argparse.ArgumentTypeError:
        logger.error("CLISUENO_START_DATE debe tener formato YYYY-MM-DD.")
        return 1

    last_day = previous_day()
    if first_day > last_day:
        logger.error("CLISUENO_START_DATE supera el último día completo.")
        return 1

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL no configurada.")
        return 1

    try:
        days = pending_days(
            database_url, first_day, last_day, limit=MAX_RECOVERY_DAYS
        )
    except AuditError:
        logger.error("No fue posible consultar días pendientes.")
        return 1

    if not days:
        logger.info("No hay días pendientes de recuperación.")
        return 0

    logger.info(
        "Recuperación: %d fechas pendientes seleccionadas, de %s a %s.",
        len(days), days[0], days[-1],
    )
    for day in days:
        if main(target_date=day) != 0:
            logger.error("Recuperación detenida en fecha: %s", day)
            return 1

    if len(days) == MAX_RECOVERY_DAYS:
        logger.info(
            "Límite de %d días alcanzado; la siguiente ejecución "
            "comprobará si quedan pendientes.",
            MAX_RECOVERY_DAYS,
        )
    return 0


def cli(argv: list[str] | None = None) -> int:
    """Interfaz de ejecución diaria o manual por fecha e intervalo."""
    parser = argparse.ArgumentParser(description="Extracción diaria MediCloud")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extrae y valida sin insertar datos en PostgreSQL",
    )
    parser.add_argument(
        "--date", type=parse_iso_date, dest="target_date",
        help="Procesar una fecha concreta, YYYY-MM-DD (hasta ayer en Colombia)",
    )
    parser.add_argument(
        "--start-date", type=parse_iso_date,
        help="Fecha inicial del intervalo manual, YYYY-MM-DD",
    )
    parser.add_argument(
        "--end-date", type=parse_iso_date,
        help="Fecha final inclusiva del intervalo manual, YYYY-MM-DD",
    )
    parser.add_argument(
        "--recover", action="store_true",
        help="Recuperar días sin success desde CLISUENO_START_DATE "
             "(máximo 7 por ejecución; requiere PostgreSQL)",
    )
    args = parser.parse_args(argv)
    if args.recover:
        if (
            args.dry_run or args.target_date is not None
            or args.start_date is not None or args.end_date is not None
        ):
            parser.error("--recover no admite --dry-run ni fechas manuales")
        return run_recovery()
    if args.target_date is not None and (
        args.start_date is not None or args.end_date is not None
    ):
        parser.error("--date no puede combinarse con --start-date/--end-date")
    if (args.start_date is None) != (args.end_date is None):
        parser.error("--start-date y --end-date deben indicarse juntos")
    if args.start_date is not None:
        return run_date_range(
            args.start_date, args.end_date, dry_run=args.dry_run
        )
    return main(dry_run=args.dry_run, target_date=args.target_date)


if __name__ == "__main__":
    sys.exit(cli())
