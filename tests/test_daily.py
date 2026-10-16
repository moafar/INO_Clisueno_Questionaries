"""Pruebas del punto de entrada de la extracción diaria."""

import argparse
from datetime import date
from unittest.mock import patch

import pytest

from src.auth import MedicloudAuthError
from src.client import MedicloudAPIError
from src.daily import main, parse_iso_date
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


@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_modo_normal_persiste_y_audita():
    from src.audit import DayResult

    lote = [
        {"id": 1, "fecha": "2026-10-14"},
        {"id": 2, "fecha": "2026-10-14"},
    ]
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.get_access_token", return_value="token-ficticio"),
        patch("src.daily.get_cuestionarios", return_value=lote),
        patch("src.daily.is_processed", return_value=False),
        patch(
            "src.daily.persist_day",
            return_value=DayResult(inserted=2, already_processed=False),
        ) as persist,
        patch("src.daily.record_failure") as failed,
    ):
        assert main() == 0
    assert persist.call_args.args[0:3] == (
        "postgresql://ficticio", date(2026, 10, 14), lote,
    )
    failed.assert_not_called()


def test_modo_simulacion_nunca_accede_a_postgresql():
    lote = [{"id": 1, "fecha": "2026-10-14"}]
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.get_access_token", return_value="token-ficticio"),
        patch("src.daily.get_cuestionarios", return_value=lote),
        patch("src.daily.is_processed") as check,
        patch("src.daily.persist_day") as persist,
        patch("src.daily.record_failure") as failed,
    ):
        assert main(dry_run=True) == 0
    check.assert_not_called()
    persist.assert_not_called()
    failed.assert_not_called()


@patch.dict("os.environ", {"DATABASE_URL": ""})
def test_modo_normal_rechaza_falta_conexion():
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.get_access_token") as auth,
        patch("src.daily.persist_day") as persist,
    ):
        assert main() == 1
    auth.assert_not_called()
    persist.assert_not_called()


@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_error_de_persistencia_no_marca_exito(caplog):
    from src.storage import StorageConflictError

    lote = [{"id": 1, "fecha": "2026-10-14"}]
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.get_access_token", return_value="token-ficticio"),
        patch("src.daily.get_cuestionarios", return_value=lote),
        patch("src.daily.is_processed", return_value=False),
        patch(
            "src.daily.persist_day",
            side_effect=StorageConflictError("dato clínico confidencial"),
        ),
        patch("src.daily.record_failure") as failed,
    ):
        assert main() == 1
    assert "dato clínico confidencial" not in caplog.text
    assert failed.call_args.kwargs == {}
    assert failed.call_args.args[4] == "STORAGE_ERROR"


@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_dia_exitoso_se_omite_sin_llamar_api():
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.is_processed", return_value=True),
        patch("src.daily.get_access_token") as auth,
        patch("src.daily.persist_day") as persist,
    ):
        assert main() == 0
    auth.assert_not_called()
    persist.assert_not_called()


@patch.dict("os.environ", {"DATABASE_URL": "postgresql://ficticio"})
def test_error_api_registra_failed_sin_datos_clinicos():
    from src.client import MedicloudAPIError

    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 14)),
        patch("src.daily.is_processed", return_value=False),
        patch("src.daily.get_access_token", return_value="token-ficticio"),
        patch(
            "src.daily.get_cuestionarios",
            side_effect=MedicloudAPIError("detalle sensible"),
        ),
        patch("src.daily.record_failure") as failed,
    ):
        assert main() == 1
    assert failed.call_args.args[4] == "API_ERROR"
    assert failed.call_args.args[5] == 0
    assert failed.call_args.args[6] == "not_available"


def test_fecha_manual_ejecuta_solo_dia_solicitado():
    requested = date(2026, 10, 10)
    lote = [{"id": 1, "fecha": requested.isoformat()}]
    with (
        patch("src.daily.load_settings") as settings,
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.get_access_token", return_value="token-ficticio"),
        patch("src.daily.get_cuestionarios", return_value=lote) as api,
        patch("src.daily.is_processed") as check,
        patch("src.daily.persist_day") as persist,
    ):
        assert main(dry_run=True, target_date=requested) == 0
    api.assert_called_once_with(
        settings=settings.return_value,
        token="token-ficticio",
        fecha_inicial=requested,
        fecha_final=requested,
    )
    check.assert_not_called()
    persist.assert_not_called()


@pytest.mark.parametrize(
    "value",
    ["2026-10-10", "2026-02-28"],
)
def test_fecha_manual_parser_valida(value):
    assert parse_iso_date(value) == date.fromisoformat(value)


@pytest.mark.parametrize(
    "value",
    ["2026-2-3", "20261010", "2026-02-30", "no-es-fecha"],
)
def test_fecha_manual_parser_rechaza_formato_invalido(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_iso_date(value)


def test_fecha_manual_rechaza_hoy_y_futuro_sin_consultar_api():
    with (
        patch("src.daily.load_settings"),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.get_access_token") as auth,
        patch("src.daily.get_cuestionarios") as api,
        patch("src.daily.is_processed") as check,
        patch("src.daily.record_failure") as failure,
    ):
        assert main(dry_run=False, target_date=date(2026, 10, 16)) == 1
    auth.assert_not_called()
    api.assert_not_called()
    check.assert_not_called()
    failure.assert_not_called()
