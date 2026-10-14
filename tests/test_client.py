from datetime import date

import pytest

from src.client import get_cuestionarios


@pytest.mark.parametrize(
    "inicio,fin",
    [
        (date(2026, 10, 10), date(2026, 10, 9)),
        (date(2026, 10, 1), date(2026, 10, 12)),
    ],
)
def test_rechaza_intervalos_invalidos(inicio, fin):
    with pytest.raises(ValueError):
        get_cuestionarios(
            settings=None,
            token="token-ficticio",
            fecha_inicial=inicio,
            fecha_final=fin,
        )
        