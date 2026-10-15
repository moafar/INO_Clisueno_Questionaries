"""Punto de entrada de la extracción diaria de cuestionarios MediCloud."""

import logging
import sys

from src.auth import MedicloudAuthError, get_access_token
from src.client import MedicloudAPIError, get_cuestionarios
from src.config import load_settings
from src.dates import previous_day

logger = logging.getLogger(__name__)


def main() -> int:
    """Extrae los cuestionarios del día anterior, sin persistirlos."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

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

        logger.info(
            "Extracción completada. Fecha: %s. Registros recibidos: %d. "
            "Persistencia: pendiente.",
            fecha,
            len(cuestionarios),
        )
        return 0

    except (ValueError, MedicloudAuthError, MedicloudAPIError):
        logger.error("La extracción diaria ha fallado.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
