"""Punto de entrada de la extracción diaria de cuestionarios MediCloud."""

import json
import logging
import sys
from datetime import UTC, datetime

from src.auth import MedicloudAuthError, get_access_token
from src.client import MedicloudAPIError, get_cuestionarios
from src.config import load_settings
from src.dates import previous_day
from src.schema import compare_schema, load_reference
from src.validation import QuestionnaireValidationError, validate_questionnaires


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


def main() -> int:
    """Extrae los cuestionarios del día anterior, sin persistirlos."""
    logger.setLevel(logging.INFO)
    if _json_handler not in logger.handlers:
        logger.addHandler(_json_handler)

    try:
        settings = load_settings()
        fecha = previous_day()

        logger.info("Inicio de extracción diaria. Fecha: %s", fecha)

        token = get_access_token(settings)
        cuestionarios = get_cuestionarios(
            settings=settings,
            token=token,
            fecha_inicial=fecha,
            fecha_final=fecha,
        )

        validate_questionnaires(cuestionarios, fecha, fecha)
        report = compare_schema(cuestionarios, load_reference())
        if report.changed:
            logger.warning(
                "Cambio de esquema detectado: campos_nuevos=%d "
                "campos_ausentes=%d registros_inconsistentes=%d",
                len(report.new_fields),
                len(report.missing_fields),
                report.inconsistent_records,
            )

        logger.info(
            "Extracción y validación completadas. Fecha: %s. Registros recibidos: %d. "
            "Persistencia: pendiente.",
            fecha,
            len(cuestionarios),
        )
        return 0

    except (ValueError, MedicloudAuthError, MedicloudAPIError, QuestionnaireValidationError):
        logger.error("La extracción diaria ha fallado.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
