"""Auditoría compartida para las cargas diarias de cuestionarios MediCloud.

Reutiliza audit.load_control sin cambiar su esquema ni las cargas de Labfp.
Las escrituras de éxito se confirman junto con los cuestionarios.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import uuid4

import psycopg

from src.storage import StorageError, store_questionnaires_in_transaction

PIPELINE = "clisueno_questionaries_daily"
TARGET_SCHEMA = "staging"
TARGET_TABLE = "clisueno_questionaries"
SOURCE_SYSTEM = "MediCloud"
SOURCE_FILE = "/apisueno/getCuestionarioSueno"
NO_HASH = "not_available"
LOCK_NAMESPACE = 72482711


class AuditError(Exception):
    """Fallo de auditoría sin detalles confidenciales."""


class ConcurrentExecutionError(AuditError):
    """Otra ejecución está procesando la misma fecha."""


@dataclass(frozen=True)
class DayResult:
    inserted: int
    already_processed: bool


def new_load_id() -> str:
    """Identificador único para un intento, independiente de la fecha."""
    return str(uuid4())


def batch_hash(records: list[dict]) -> str:
    """SHA-256 del contenido, estable ante cambios de orden del lote y claves."""
    try:
        ordered = sorted(records, key=lambda record: record["id"])
        payload = json.dumps(
            ordered, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError("Lote no apto para calcular hash") from exc
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _success_exists(cur: psycopg.Cursor, day: date) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM audit.load_control
        WHERE pipeline_name = %s
          AND target_schema = %s
          AND target_table = %s
          AND source_start_date = %s
          AND source_end_date = %s
          AND status = 'success'
        LIMIT 1
        """,
        (PIPELINE, TARGET_SCHEMA, TARGET_TABLE, day, day),
    )
    return cur.fetchone() is not None


def is_processed(database_url: str, day: date) -> bool:
    """Comprueba si el día tiene una carga confirmada de este pipeline."""
    try:
        with (
            psycopg.connect(database_url) as conn,
            conn.cursor() as cur,
        ):
            return _success_exists(cur, day)
    except psycopg.Error as exc:
        raise AuditError("Error consultando fechas procesadas") from exc


def persist_day(
    database_url: str,
    day: date,
    records: list[dict],
    started_at: datetime,
    load_id: str,
) -> DayResult:
    """Confirma cuestionarios y auditoría success en una única transacción.

    Bloquea la fecha de este pipeline y vuelve a comprobar success tras el bloqueo.
    No marca como completado un día hasta terminar el commit PostgreSQL.
    """
    digest = batch_hash(records)
    try:
        with (
            psycopg.connect(database_url, autocommit=True) as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            cur.execute(
                "SELECT pg_try_advisory_xact_lock(%s, %s)",
                (LOCK_NAMESPACE, day.toordinal()),
            )
            if not cur.fetchone()[0]:
                raise ConcurrentExecutionError("Ya existe una carga activa para esta fecha")

            if _success_exists(cur, day):
                return DayResult(inserted=0, already_processed=True)

            inserted = store_questionnaires_in_transaction(conn, records)
            cur.execute(
                """
                INSERT INTO audit.load_control (
                    load_id, pipeline_name, target_schema, target_table,
                    source_system, source_start_date, source_end_date,
                    source_file, source_file_hash, rows_read, rows_loaded,
                    started_at, finished_at, status, error_message
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, 'success', NULL
                )
                """,
                (
                    load_id, PIPELINE, TARGET_SCHEMA, TARGET_TABLE,
                    SOURCE_SYSTEM, day, day, SOURCE_FILE, digest,
                    len(records), inserted, started_at, datetime.now(UTC),
                ),
            )
        return DayResult(inserted=inserted, already_processed=False)
    except psycopg.Error as exc:
        raise AuditError("Error confirmando cuestionarios y auditoría") from exc


def record_failure(
    database_url: str,
    day: date,
    started_at: datetime,
    load_id: str,
    category: str,
    rows_read: int = 0,
    source_hash: str = NO_HASH,
) -> None:
    """Audita un fallo en una transacción independiente, sin datos clínicos."""
    categories = {
        "AUTH_ERROR", "API_ERROR", "VALIDATION_ERROR", "SCHEMA_ERROR",
        "STORAGE_ERROR", "AUDIT_ERROR", "CONFIG_ERROR",
    }
    if category not in categories:
        raise AuditError("Categoría de fallo no permitida")
    try:
        with (
            psycopg.connect(database_url) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                INSERT INTO audit.load_control (
                    load_id, pipeline_name, target_schema, target_table,
                    source_system, source_start_date, source_end_date,
                    source_file, source_file_hash, rows_read, rows_loaded,
                    started_at, finished_at, status, error_message
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, 0, %s, %s, 'failed', %s
                )
                """,
                (
                    load_id, PIPELINE, TARGET_SCHEMA, TARGET_TABLE,
                    SOURCE_SYSTEM, day, day, SOURCE_FILE, source_hash,
                    rows_read, started_at, datetime.now(UTC), category,
                ),
            )
    except psycopg.Error as exc:
        raise AuditError("Error registrando fallo en auditoría") from exc
