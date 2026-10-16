"""Pruebas sin conexión real ni datos clínicos."""

from contextlib import contextmanager
from unittest.mock import patch

import pytest

from src.storage import (
    StorageConflictError,
    StorageError,
    content_hash,
    store_questionnaires,
    store_questionnaires_in_transaction,
)


class FakeCursor:
    def __init__(self, existing=None):
        self.rows = dict(existing or {})
        self.pending = {}
        self.result = None

    def execute(self, query, params):
        if "INSERT INTO" in query:
            identifier = params[0]
            if identifier in self.rows or identifier in self.pending:
                self.result = None
            else:
                self.pending[identifier] = params[-1]
                self.result = (identifier,)
        elif "SELECT hash_contenido" in query:
            identifier = params[0]
            digest = self.rows.get(identifier, self.pending.get(identifier))
            self.result = (digest,) if digest is not None else None
        else:
            raise AssertionError("SQL inesperado")

    def fetchone(self):
        return self.result

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class FakeConnection:
    def __init__(self, existing=None):
        self.cur = FakeCursor(existing)
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.cur

    @contextmanager
    def transaction(self):
        try:
            yield
        except Exception:
            self.cur.pending.clear()
            self.rolled_back = True
            raise
        else:
            self.cur.rows.update(self.cur.pending)
            self.cur.pending.clear()
            self.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def sample(identifier=1, name="ficticio"):
    return {
        "id": identifier,
        "fecha": "2026-10-14",
        "Documento": name,
        "tipoDocumento": "CC",
        "Sede": None,
    }


def test_hash_determinista_sin_dependencia_del_orden():
    left = {"id": 1, "texto": "á", "valor": [1, None]}
    right = {"valor": [1, None], "texto": "á", "id": 1}
    assert content_hash(left) == content_hash(right)
    assert len(content_hash(left)) == 64


def test_inserta_un_lote_y_confirma():
    conn = FakeConnection()
    with patch("src.storage.psycopg.connect", return_value=conn):
        assert store_questionnaires("postgresql://ficticio", [sample(1), sample(2)]) == 2
    assert conn.committed
    assert len(conn.cur.rows) == 2


def test_repetir_lote_es_idempotente():
    record = sample()
    conn = FakeConnection({1: content_hash(record)})
    with patch("src.storage.psycopg.connect", return_value=conn):
        assert store_questionnaires("postgresql://ficticio", [record]) == 0
    assert conn.committed
    assert len(conn.cur.rows) == 1


def test_conflicto_provoca_rollback_total():
    conn = FakeConnection({2: content_hash(sample(2, "anterior"))})
    with (
        patch("src.storage.psycopg.connect", return_value=conn),
        pytest.raises(StorageConflictError, match="contenido diferente"),
    ):
        store_questionnaires(
                "postgresql://ficticio", [sample(1), sample(2, "nuevo")]
            )
    assert conn.rolled_back
    assert 1 not in conn.cur.rows


def test_rechaza_ids_duplicados_antes_de_conectar():
    with (
        patch("src.storage.psycopg.connect") as connect,
        pytest.raises(StorageError, match="repetido"),
    ):
        store_questionnaires("postgresql://ficticio", [sample(), sample()])
    connect.assert_not_called()


def test_rechaza_fecha_invalida_antes_de_conectar():
    record = sample()
    record["fecha"] = "2026-02-30"
    with (
        patch("src.storage.psycopg.connect") as connect,
        pytest.raises(StorageError, match="Fecha"),
    ):
        store_questionnaires("postgresql://ficticio", [record])
    connect.assert_not_called()


def test_rechaza_json_no_serializable():
    with pytest.raises(StorageError, match="serializable"):
        content_hash({"valor": object()})


def test_lote_vacio_no_inserta_registros():
    conn = FakeConnection()
    with patch("src.storage.psycopg.connect", return_value=conn):
        assert store_questionnaires("postgresql://ficticio", []) == 0
    assert conn.committed


def test_shared_connection_keeps_commit_in_caller():
    conn = FakeConnection()
    with conn.transaction():
        assert store_questionnaires_in_transaction(conn, [sample()]) == 1
        assert not conn.committed
        assert 1 not in conn.cur.rows
    assert conn.committed
    assert 1 in conn.cur.rows


def test_shared_connection_rollback_is_owned_by_caller():
    conn = FakeConnection()
    with pytest.raises(RuntimeError, match="fallo simulado"), conn.transaction():
        store_questionnaires_in_transaction(conn, [sample()])
        raise RuntimeError("fallo simulado")
    assert conn.rolled_back
    assert conn.cur.rows == {}


def test_shared_connection_conflict_rolls_back_earlier_insert():
    conn = FakeConnection({2: content_hash(sample(2, "original"))})
    with pytest.raises(StorageConflictError), conn.transaction():
        store_questionnaires_in_transaction(conn, [sample(1), sample(2, "otro")])
    assert conn.rolled_back
    assert 1 not in conn.cur.rows
