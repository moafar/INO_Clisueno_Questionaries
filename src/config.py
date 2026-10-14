import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_url: str
    app_id: str
    app_key: str
    resource: str
    api_version: str


def load_settings() -> Settings:
    load_dotenv()

    required = {
        "MEDICLOUD_BASE_URL": os.getenv("MEDICLOUD_BASE_URL"),
        "MEDICLOUD_APP_ID": os.getenv("MEDICLOUD_APP_ID"),
        "MEDICLOUD_APP_KEY": os.getenv("MEDICLOUD_APP_KEY"),
        "MEDICLOUD_RESOURCE": os.getenv("MEDICLOUD_RESOURCE"),
        "MEDICLOUD_API_VERSION": os.getenv("MEDICLOUD_API_VERSION"),
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"Faltan variables de configuración: {', '.join(missing)}"
        )

    return Settings(
        base_url=required["MEDICLOUD_BASE_URL"].rstrip("/"),
        app_id=required["MEDICLOUD_APP_ID"],
        app_key=required["MEDICLOUD_APP_KEY"],
        resource=required["MEDICLOUD_RESOURCE"],
        api_version=required["MEDICLOUD_API_VERSION"],
    )
