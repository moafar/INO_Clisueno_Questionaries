"""Pruebas del punto de entrada de la extracción diaria."""

from datetime import date
from unittest.mock import patch

import pytest

from src.auth import MedicloudAuthError
from src.client import MedicloudAPIError
from src.daily import main


@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_extraccion_correcta(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.return_value = [{"id": 1}, {"id": 2}]

    assert main() == 0

    mock_cuestionarios.assert_called_once_with(
        settings=mock_settings.return_value,
        token="token-ficticio",
        fecha_inicial=date(2026, 10, 14),
        fecha_final=date(2026, 10, 14),
    )


@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_error_autenticacion(
    mock_settings, mock_fecha, mock_token
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.side_effect = MedicloudAuthError("Error de autenticación")

    assert main() == 1


@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_error_extraccion(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.side_effect = MedicloudAPIError("Error API")

    assert main() == 1


@patch("src.daily.load_settings")
def test_error_configuracion(mock_settings):
    mock_settings.side_effect = ValueError("Configuración incompleta")

    assert main() == 1


@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_dia_sin_cuestionarios(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.return_value = []

    assert main() == 0


@pytest.mark.parametrize(
    "exception",
    [MedicloudAuthError("Error"), MedicloudAPIError("Error")],
)
def test_errores_no_exponen_detalles_en_logs(exception, caplog):
    with patch("src.daily.load_settings"), \
         patch("src.daily.previous_day"), \
         patch("src.daily.get_access_token", side_effect=exception):
        assert main() == 1

    assert "Error" not in caplog.text
    assert "La extracción diaria ha fallado." in caplog.text
