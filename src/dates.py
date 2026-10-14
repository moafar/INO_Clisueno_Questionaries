from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Bogota")


def previous_day(now: datetime | None = None) -> date:
    """Devuelve el día anterior según la hora de Colombia."""

    if now is None:
        now = datetime.now(TIMEZONE)
    elif now.tzinfo is None:
        raise ValueError("La fecha debe incluir zona horaria")
    else:
        now = now.astimezone(TIMEZONE)

    return now.date() - timedelta(days=1)
