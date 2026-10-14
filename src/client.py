from datetime import date

import requests

from src.config import Settings


class MedicloudAPIError(Exception):
    """Error al consultar la API de MediCloud."""


def get_cuestionarios(
    settings: Settings,
    token: str,
    fecha_inicial: date,
    fecha_final: date,
) -> list[dict]:

    diferencia = (fecha_final - fecha_inicial).days

    if not 0 <= diferencia <= 10:
        raise ValueError(
            "El intervalo debe estar entre 0 y 10 días."
        )

    url = f"{settings.base_url}/apisueno/getCuestionarioSueno"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    data = {
        "fechaInicial": fecha_inicial.isoformat(),
        "fechaFinal": fecha_final.isoformat(),
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            timeout=(10, 120),
        )
        response.raise_for_status()
        payload = response.json()

    except (requests.RequestException, ValueError) as exc:
        raise MedicloudAPIError(
            "Error de comunicación o respuesta inválida de MediCloud"
        ) from exc

    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(payload.get("datos"), list)
    ):
        raise MedicloudAPIError(
            "La API no devolvió una lista válida de cuestionarios"
        )

    if not all(isinstance(item, dict) for item in payload["datos"]):
        raise MedicloudAPIError(
            "La respuesta contiene registros con estructura inválida"
        )

    return payload["datos"]
