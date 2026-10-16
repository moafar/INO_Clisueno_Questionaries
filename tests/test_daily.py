"""Pruebas del punto de entrada de la extracción diaria."""

from datetime import date
from unittest.mock import patch

import pytest

from src.auth import MedicloudAuthError
from src.client import MedicloudAPIError
from src.daily import main
from src.validation import QuestionnaireValidationError


@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_extraccion_correcta(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.return_value = [
        {"id": 1, "fecha": "2026-10-14"},
        {"id": 2, "fecha": "2026-10-14"},
    ]

    assert main(dry_run=True) == 0

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

    assert main(dry_run=True) == 1


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

    assert main(dry_run=True) == 1


@patch("src.daily.load_settings")
def test_error_configuracion(mock_settings):
    mock_settings.side_effect = ValueError("Configuración incompleta")

    assert main(dry_run=True) == 1


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

    assert main(dry_run=True) == 0


@pytest.mark.parametrize(
    "exception",
    [MedicloudAuthError("Error"), MedicloudAPIError("Error")],
)
def test_errores_no_exponen_detalles_en_logs(exception, caplog):
    with patch("src.daily.load_settings"), \
         patch("src.daily.previous_day"), \
         patch("src.daily.get_access_token", side_effect=exception):
        assert main(dry_run=True) == 1

    assert "Error" not in caplog.text
    assert "La extracción diaria ha fallado." in caplog.text


@patch("src.daily.validate_questionnaires")
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_diario_valida_lote_y_fecha(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_validate
):
    fecha = date(2026, 10, 14)
    mock_fecha.return_value = fecha
    mock_token.return_value = "token-ficticio"
    lote = [{"id": 1, "fecha": fecha.isoformat()}]
    mock_cuestionarios.return_value = lote

    assert main(dry_run=True) == 0
    mock_validate.assert_called_once_with(lote, fecha, fecha)


@patch("src.daily.validate_questionnaires")
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_error_validacion_no_marca_exito(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_validate, caplog
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.return_value = [{"id": 1, "fecha": "2026-10-14"}]
    mock_validate.side_effect = QuestionnaireValidationError(
        "contenido clínico confidencial"
    )

    assert main(dry_run=True) == 1
    assert "contenido clínico confidencial" not in caplog.text
    assert "La extracción diaria ha fallado." in caplog.text


@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token")
@patch("src.daily.previous_day")
@patch("src.daily.load_settings")
def test_lote_realmente_invalido_se_rechaza(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios
):
    mock_fecha.return_value = date(2026, 10, 14)
    mock_token.return_value = "token-ficticio"
    mock_cuestionarios.return_value = [{"id": 1, "fecha": "2026-10-13"}]

    assert main(dry_run=True) == 1


@patch("src.daily.store_questionnaires", return_value=2)
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token", return_value="token-ficticio")
@patch("src.daily.previous_day", return_value=date(2026, 10, 14))
@patch("src.daily.load_settings")
@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_modo_normal_persiste(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_storage
):
    lote = [
        {"id": 1, "fecha": "2026-10-14"},
        {"id": 2, "fecha": "2026-10-14"},
    ]
    mock_cuestionarios.return_value = lote
    assert main() == 0
    mock_storage.assert_called_once_with("postgresql://ficticio", lote)


@patch("src.daily.store_questionnaires")
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token", return_value="token-ficticio")
@patch("src.daily.previous_day", return_value=date(2026, 10, 14))
@patch("src.daily.load_settings")
def test_modo_simulacion_nunca_persiste(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_storage
):
    mock_cuestionarios.return_value = [{"id": 1, "fecha": "2026-10-14"}]
    assert main(dry_run=True) == 0
    mock_storage.assert_not_called()


@patch("src.daily.store_questionnaires")
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token", return_value="token-ficticio")
@patch("src.daily.previous_day", return_value=date(2026, 10, 14))
@patch("src.daily.load_settings")
@patch.dict("os.environ", {"DATABASE_URL": ""})
def test_modo_normal_rechaza_falta_conexion(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_storage
):
    mock_cuestionarios.return_value = []
    assert main() == 1
    mock_storage.assert_not_called()


@patch("src.daily.store_questionnaires")
@patch("src.daily.get_cuestionarios")
@patch("src.daily.get_access_token", return_value="token-ficticio")
@patch("src.daily.previous_day", return_value=date(2026, 10, 14))
@patch("src.daily.load_settings")
@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_error_de_persistencia_no_marca_exito(
    mock_settings, mock_fecha, mock_token, mock_cuestionarios, mock_storage, caplog
):
    from src.storage import StorageConflictError

    mock_cuestionarios.return_value = [{"id": 1, "fecha": "2026-10-14"}]
    mock_storage.side_effect = StorageConflictError("dato clínico confidencial")
    assert main() == 1
    assert "dato clínico confidencial" not in caplog.text
