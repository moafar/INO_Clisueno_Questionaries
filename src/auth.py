
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

    retry = Retry(
        total=2,  # 2 reintentos + 1 intento inicial
        connect=2,
        read=0,
        status=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"POST"},
        respect_retry_after_header=True,
    )

    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        response = session.post(
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

    finally:
        session.close()

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
