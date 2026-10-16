"""Punto de entrada de la extracción diaria de cuestionarios MediCloud."""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime

from src.audit import (
    AuditError,
    NO_HASH,
    batch_hash,
    is_processed,
    new_load_id,
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


def main(dry_run: bool = False) -> int:
    """Extrae y valida; en modo normal confirma carga y auditoría juntas."""
    logger.setLevel(logging.INFO)
    if _json_handler not in logger.handlers:
        logger.addHandler(_json_handler)

    started_at = datetime.now(UTC)
    load_id = new_load_id()
    fecha = None
    database_url = None
    rows_read = 0
    source_hash = NO_HASH
    category = "CONFIG_ERROR"

    try:
        settings = load_settings()
        fecha = previous_day()

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extracción diaria MediCloud")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extrae y valida sin insertar datos en PostgreSQL",
    )
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run))
