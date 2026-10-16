"""Pruebas sin conexiones reales de la auditoría compartida MediCloud."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.audit import (
    NO_HASH,
    AuditError,
    ConcurrentExecutionError,
    batch_hash,
    is_processed,
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
    assert NO_HASH in params
    assert params[-1] == "API_ERROR"


def test_fallo_rechaza_mensajes_no_permitidos():
    with patch("src.audit.psycopg.connect") as connect, pytest.raises(AuditError):
        record_failure(DB, DAY, STARTED, "run-3", "texto clínico libre")
    connect.assert_not_called()
