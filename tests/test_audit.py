"""Pruebas sin conexiones reales de la auditoría compartida MediCloud."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from src.audit import (
    NO_HASH,
    AuditError,
    ConcurrentExecutionError,
    batch_hash,
    exclusive_recovery,
    is_processed,
    pending_days,
    persist_day,
    record_failure,
)

DAY = date(2026, 10, 15)
STARTED = datetime(2026, 10, 16, 8, tzinfo=UTC)
DB = "postgresql://ficticio"


def fake_connection(fetch_results=()):
    conn = MagicMock()
    # Un context manager de psycopg devuelve la misma conexión.
    # MagicMock, en cambio, crea otro objeto salvo que lo configuremos.
    conn.__enter__.return_value = conn
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.side_effect = list(fetch_results)
    return conn, cur


def sample(identifier):
    return {"id": identifier, "fecha": "2026-10-15", "Documento": "FICTICIO"}


def test_hash_de_lote_es_estable_a_orden_y_claves():
    one = [sample(2), sample(1)]
    two = [
        {"Documento": "FICTICIO", "fecha": "2026-10-15", "id": 1},
        sample(2),
    ]
    assert batch_hash(one) == batch_hash(two)
    assert len(batch_hash([])) == 64


def test_hash_rechaza_objetos_no_serializables():
    with pytest.raises(AuditError, match="hash"):
        batch_hash([{"id": 1, "valor": object()}])


def test_exito_escribe_cuestionarios_y_auditoria_en_misma_conexion():
    conn, cur = fake_connection([(True,), None])
    records = [sample(1), sample(2)]
    with (
        patch("src.audit.psycopg.connect", return_value=conn) as connect,
        patch("src.audit.store_questionnaires_in_transaction", return_value=2) as write,
    ):
        result = persist_day(DB, DAY, records, STARTED, "run-1")

    assert result.inserted == 2
    assert not result.already_processed
    assert connect.call_args.kwargs == {"autocommit": True}
    write.assert_called_once_with(conn, records)
    inserts = [
        call for call in cur.execute.call_args_list
        if "INSERT INTO audit.load_control" in call.args[0]
    ]
    assert len(inserts) == 1
    params = inserts[0].args[1]
    assert params[0] == "run-1"
    assert params[8] == batch_hash(records)
    assert params[9:11] == (2, 2)


def test_dia_previamente_procesado_no_inserta_ni_audita_de_nuevo():
    conn, cur = fake_connection([(True,), (1,)])
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        patch("src.audit.store_questionnaires_in_transaction") as write,
    ):
        result = persist_day(DB, DAY, [sample(1)], STARTED, "run-1")
    assert result.already_processed
    write.assert_not_called()
    assert all(
        "INSERT INTO audit.load_control" not in call.args[0]
        for call in cur.execute.call_args_list
    )


def test_ejecucion_concurrente_es_rechazada():
    conn, _ = fake_connection([(False,)])
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        patch("src.audit.store_questionnaires_in_transaction") as write,
        pytest.raises(ConcurrentExecutionError),
    ):
        persist_day(DB, DAY, [sample(1)], STARTED, "run-1")
    write.assert_not_called()


def test_fallo_en_carga_no_insertara_success():
    from src.storage import StorageConflictError

    conn, cur = fake_connection([(True,), None])
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        patch(
            "src.audit.store_questionnaires_in_transaction",
            side_effect=StorageConflictError("conflicto"),
        ),
        pytest.raises(StorageConflictError),
    ):
        persist_day(DB, DAY, [sample(1)], STARTED, "run-1")
    assert all(
        "INSERT INTO audit.load_control" not in call.args[0]
        for call in cur.execute.call_args_list
    )


def test_dia_procesado_consulta_solo_pipeline_y_success():
    conn, cur = fake_connection([(1,)])
    with patch("src.audit.psycopg.connect", return_value=conn):
        assert is_processed(DB, DAY)
    sql, params = cur.execute.call_args.args
    assert "status = 'success'" in sql
    assert params[0] == "clisueno_questionaries_daily"
    assert params[-2:] == (DAY, DAY)


def test_fallo_registra_codigo_seguro_en_audit_load_control():
    conn, cur = fake_connection()
    with patch("src.audit.psycopg.connect", return_value=conn):
        record_failure(DB, DAY, STARTED, "run-2", "API_ERROR", rows_read=0)
    sql, params = cur.execute.call_args.args
    assert "'failed'" in sql
    assert params[0] == "run-2"
    assert params[8] == f"failed:run-2:{NO_HASH}"
    assert params[-1] == "API_ERROR"


def test_fallo_rechaza_mensajes_no_permitidos():
    with patch("src.audit.psycopg.connect") as connect, pytest.raises(AuditError):
        record_failure(DB, DAY, STARTED, "run-3", "texto clínico libre")
    connect.assert_not_called()


def test_fallos_repetidos_misma_fecha_y_hash_tienen_valores_unicos():
    """El índice único no debe bloquear intentos fallidos repetidos."""
    hashes = []
    for load_id in ("run-3", "run-4"):
        conn, cur = fake_connection()
        with patch("src.audit.psycopg.connect", return_value=conn):
            record_failure(
                DB, DAY, STARTED, load_id, "STORAGE_ERROR",
                rows_read=2, source_hash="a" * 64,
            )
        hashes.append(cur.execute.call_args.args[1][8])

    assert hashes == [
        "failed:run-3:" + "a" * 64,
        "failed:run-4:" + "a" * 64,
    ]
    assert hashes[0] != hashes[1]


def test_fallos_sin_respuesta_tambien_tienen_valores_unicos():
    hashes = []
    for load_id in ("run-5", "run-6"):
        conn, cur = fake_connection()
        with patch("src.audit.psycopg.connect", return_value=conn):
            record_failure(DB, DAY, STARTED, load_id, "API_ERROR")
        hashes.append(cur.execute.call_args.args[1][8])

    assert hashes == [
        "failed:run-5:not_available",
        "failed:run-6:not_available",
    ]


def test_pending_days_busca_solo_fechas_sin_success_de_clisueno():
    first = date(2026, 10, 10)
    last = date(2026, 10, 15)
    conn, cur = fake_connection()
    cur.fetchall.return_value = [(first,), (date(2026, 10, 12),)]
    with patch("src.audit.psycopg.connect", return_value=conn):
        pending = pending_days(DB, first, last, limit=2)
    assert pending == [first, date(2026, 10, 12)]
    sql, params = cur.execute.call_args.args
    assert "generate_series(" in sql
    assert "NOT EXISTS" in sql
    assert "audit.status = 'success'" in sql
    assert "audit.source_start_date = days.day::date" in sql
    assert "audit.source_end_date = days.day::date" in sql
    assert params == (
        first, last, "clisueno_questionaries_daily",
        "staging", "clisueno_questionaries", 2,
    )
    assert "LIMIT %s" in sql


@pytest.mark.parametrize(
    "first,last,limit",
    [
        (date(2026, 10, 15), date(2026, 10, 14), 7),
        (date(2026, 10, 14), date(2026, 10, 15), 0),
    ],
)
def test_pending_days_rechaza_limites_invalidos_sin_conexion(
    first, last, limit
):
    with (
        patch("src.audit.psycopg.connect") as connect,
        pytest.raises(ValueError),
    ):
        pending_days(DB, first, last, limit=limit)
    connect.assert_not_called()


def test_pending_days_traduce_fallo_de_postgresql_en_error_seguro():
    conn, cur = fake_connection()
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        patch.object(cur, "execute", side_effect=psycopg.OperationalError()),
        pytest.raises(AuditError, match="días pendientes"),
    ):
        pending_days(DB, date(2026, 10, 14), DAY)


def test_bloqueo_recuperacion_dura_todo_el_contexto():
    conn, cur = fake_connection([(True,)])
    with patch("src.audit.psycopg.connect", return_value=conn) as connect:
        with exclusive_recovery(DB):
            conn.close.assert_not_called()
    sql, params = cur.execute.call_args.args
    assert "pg_try_advisory_lock" in sql
    assert params == (72482711, 0)
    assert connect.call_args.kwargs == {"autocommit": True}
    conn.close.assert_called_once_with()


def test_bloqueo_recuperacion_ocupado_rechaza_segunda_ejecucion():
    conn, _ = fake_connection([(False,)])
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        pytest.raises(ConcurrentExecutionError),
    ):
        with exclusive_recovery(DB):
            pytest.fail("No debe iniciar recuperación")
    conn.close.assert_called_once_with()


def test_bloqueo_recuperacion_se_libera_tras_error():
    conn, _ = fake_connection([(True,)])
    with (
        patch("src.audit.psycopg.connect", return_value=conn),
        pytest.raises(RuntimeError, match="simulado"),
    ):
        with exclusive_recovery(DB):
            raise RuntimeError("simulado")
    conn.close.assert_called_once_with()


def test_bloqueo_recuperacion_error_conexion_no_expone_detalles():
    with (
        patch(
            "src.audit.psycopg.connect",
            side_effect=psycopg.OperationalError("clave secreta"),
        ),
        pytest.raises(AuditError, match="bloqueo de recuperación") as exc,
    ):
        with exclusive_recovery(DB):
            pytest.fail("No debe entrar")
    assert "clave secreta" not in str(exc.value)
