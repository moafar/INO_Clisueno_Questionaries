import requests

from src.config import Settings


class MedicloudAuthError(Exception):
    """Error durante la autenticación con MediCloud."""


def get_access_token(settings: Settings) -> str:
    url = f"{settings.base_url}/auth/getToken"

    headers = {
        "App_Id": settings.app_id,
        "App_Key": settings.app_key,
        "Resource": settings.resource,
        "ApiVersion": settings.api_version,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            timeout=(10, 30),
        )
        response.raise_for_status()
        payload = response.json()

    except (requests.RequestException, ValueError) as exc:
        raise MedicloudAuthError(
            "Error de comunicación o respuesta inválida de MediCloud"
        ) from exc

    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or not isinstance(payload.get("access_token"), str)
        or not payload["access_token"]
    ):
        raise MedicloudAuthError(
            "MediCloud no devolvió un token válido"
        )

    return payload["access_token"]
