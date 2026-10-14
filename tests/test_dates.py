from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from src.dates import previous_day


def test_dia_anterior_colombia():
    now = datetime(2026, 10, 14, 3, 0, tzinfo=ZoneInfo("America/Bogota"))

    assert previous_day(now) == date(2026, 10, 13)


def test_conversion_desde_utc():
    now = datetime(2026, 10, 14, 2, 0, tzinfo=ZoneInfo("UTC"))

    assert previous_day(now) == date(2026, 10, 12)


def test_cambio_de_mes():
    now = datetime(2026, 11, 1, 3, 0, tzinfo=ZoneInfo("America/Bogota"))

    assert previous_day(now) == date(2026, 10, 31)


def test_rechaza_fecha_sin_zona_horaria():
    now = datetime(2026, 10, 14, 3, 0)

    with pytest.raises(ValueError):
        previous_day(now)
