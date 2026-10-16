"""Pruebas del punto de entrada de la extracción diaria."""

import argparse
from datetime import date
from unittest.mock import call, patch

import pytest

from src.audit import AuditError
from src.auth import MedicloudAuthError
from src.client import MedicloudAPIError
from src.daily import cli, main, parse_iso_date, run_date_range, run_recovery
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


def test_intervalo_manual_procesa_dias_consecutivos_inclusivos():
    with (
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.main", return_value=0) as process,
    ):
        assert run_date_range(
            date(2026, 10, 1), date(2026, 10, 3), dry_run=True
        ) == 0
    assert process.call_args_list == [
        call(dry_run=True, target_date=date(2026, 10, 1)),
        call(dry_run=True, target_date=date(2026, 10, 2)),
        call(dry_run=True, target_date=date(2026, 10, 3)),
    ]


def test_intervalo_detiene_siguientes_dias_si_un_dia_falla():
    with (
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.main", side_effect=[0, 1, 0]) as process,
    ):
        assert run_date_range(
            date(2026, 10, 1), date(2026, 10, 3)
        ) == 1
    assert process.call_count == 2
    assert process.call_args_list[-1] == call(
        dry_run=False, target_date=date(2026, 10, 2)
    )


@pytest.mark.parametrize(
    "start,end",
    [
        (date(2026, 10, 3), date(2026, 10, 2)),
        (date(2026, 10, 1), date(2026, 10, 16)),
    ],
)
def test_intervalo_invalido_no_ejecuta_ningun_dia(start, end):
    with (
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.main") as process,
    ):
        assert run_date_range(start, end, dry_run=True) == 1
    process.assert_not_called()


def test_cli_encamina_intervalo_a_procesamiento_diario():
    start, end = date(2026, 10, 1), date(2026, 10, 3)
    with patch("src.daily.run_date_range", return_value=0) as run:
        assert cli([
            "--start-date", start.isoformat(),
            "--end-date", end.isoformat(), "--dry-run",
        ]) == 0
    run.assert_called_once_with(start, end, dry_run=True)


@pytest.mark.parametrize(
    "args",
    [
        ["--start-date", "2026-10-01"],
        ["--end-date", "2026-10-03"],
        ["--date", "2026-10-02", "--start-date", "2026-10-01"],
        ["--date", "2026-10-02", "--end-date", "2026-10-03"],
    ],
)
def test_cli_rechaza_intervalos_incompletos_y_combinaciones(args):
    with (
        patch("src.daily.main") as process,
        patch("src.daily.run_date_range") as run,
        pytest.raises(SystemExit) as exc,
    ):
        cli(args)
    assert exc.value.code == 2
    process.assert_not_called()
    run.assert_not_called()


def test_cli_mantiene_opcion_manual_fecha_individual():
    day = date(2026, 10, 10)
    with patch("src.daily.main", return_value=0) as process:
        assert cli(["--date", day.isoformat(), "--dry-run"]) == 0
    process.assert_called_once_with(dry_run=True, target_date=day)


def test_cli_mantiene_opcion_diaria_por_defecto():
    with patch("src.daily.main", return_value=0) as process:
        assert cli([]) == 0
    process.assert_called_once_with(dry_run=False, target_date=None)


def test_recovery_procesa_solo_pendientes_en_orden():
    days = [date(2026, 10, 10), date(2026, 10, 12), date(2026, 10, 15)]
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": "2026-10-10",
            "DATABASE_URL": "postgresql://ficticio",
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days", return_value=days) as fetch,
        patch("src.daily.main", return_value=0) as process,
    ):
        assert run_recovery() == 0
    fetch.assert_called_once_with(
        "postgresql://ficticio", date(2026, 10, 10),
        date(2026, 10, 15), limit=7,
    )
    assert process.call_args_list == [
        call(target_date=day) for day in days
    ]


def test_recovery_interrumpe_en_primer_dia_fallido():
    days = [date(2026, 10, 10), date(2026, 10, 11), date(2026, 10, 12)]
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": "2026-10-10",
            "DATABASE_URL": "postgresql://ficticio",
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days", return_value=days),
        patch("src.daily.main", side_effect=[0, 1, 0]) as process,
    ):
        assert run_recovery() == 1
    assert process.call_args_list == [
        call(target_date=days[0]), call(target_date=days[1]),
    ]


def test_recovery_sin_pendientes_no_consulta_medicloud():
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": "2026-10-10",
            "DATABASE_URL": "postgresql://ficticio",
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days", return_value=[]),
        patch("src.daily.main") as process,
    ):
        assert run_recovery() == 0
    process.assert_not_called()


@pytest.mark.parametrize(
    "start, database",
    [
        ("", "postgresql://ficticio"),
        ("formato-invalido", "postgresql://ficticio"),
        ("2026-10-16", "postgresql://ficticio"),
        ("2026-10-10", ""),
    ],
)
def test_recovery_configuracion_invalida_nunca_consulta_auditoria(
    start, database
):
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": start,
            "DATABASE_URL": database,
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days") as fetch,
        patch("src.daily.main") as process,
    ):
        assert run_recovery() == 1
    fetch.assert_not_called()
    process.assert_not_called()


def test_recovery_fallo_auditoria_no_ejecuta_dias():
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": "2026-10-10",
            "DATABASE_URL": "postgresql://ficticio",
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days", side_effect=AuditError("secreto")),
        patch("src.daily.main") as process,
    ):
        assert run_recovery() == 1
    process.assert_not_called()


def test_recovery_limite_siete_por_ejecucion():
    from datetime import timedelta

    days = [date(2026, 10, 1) + timedelta(days=offset) for offset in range(7)]
    with (
        patch("src.daily.load_dotenv"),
        patch.dict("os.environ", {
            "CLISUENO_START_DATE": "2026-10-01",
            "DATABASE_URL": "postgresql://ficticio",
        }),
        patch("src.daily.previous_day", return_value=date(2026, 10, 15)),
        patch("src.daily.pending_days", return_value=days) as fetch,
        patch("src.daily.main", return_value=0) as process,
    ):
        assert run_recovery() == 0
    assert fetch.call_args.kwargs["limit"] == 7
    assert process.call_count == 7


@pytest.mark.parametrize(
    "arguments",
    [
        ["--recover", "--dry-run"],
        ["--recover", "--date", "2026-10-10"],
        ["--recover", "--start-date", "2026-10-09", "--end-date", "2026-10-10"],
    ],
)
def test_cli_recovery_no_admite_simulacion_ni_fechas_manuales(arguments):
    with (
        patch("src.daily.run_recovery") as recover,
        patch("src.daily.main") as process,
        pytest.raises(SystemExit) as exc,
    ):
        cli(arguments)
    assert exc.value.code == 2
    recover.assert_not_called()
    process.assert_not_called()


def test_cli_recovery_solo_se_activa_explicitamente():
    with patch("src.daily.run_recovery", return_value=0) as recover:
        assert cli(["--recover"]) == 0
    recover.assert_called_once_with()
