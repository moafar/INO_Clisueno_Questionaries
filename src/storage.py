
"""Persistencia transaccional e idempotente de cuestionarios MediCloud.

No emite datos clínicos, identificadores ni cadenas de conexión a los logs.
La unicidad global de `id` se considera un supuesto contractual.
"""

import hashlib
import json
from datetime import date

import psycopg
from psycopg.types.json import Jsonb


class StorageError(Exception):
    """Fallo de almacenamiento sin contenido clínico en el mensaje."""


class StorageConflictError(StorageError):
    """Un identificador ya existe con otro contenido."""


def content_hash(record: dict) -> str:
    """SHA-256 del JSON original con claves ordenadas, UTF-8 y sin espacios."""
    try:
        serialized = json.dumps(
            record,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StorageError(
            "Registro no serializable como JSON válido"
        ) from exc

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _optional_text(record: dict, field: str) -> str | None:
    value = record.get(field)

    if value is not None and not isinstance(value, str):
        raise StorageError("Metadato de cuestionario de tipo inválido")

    return value


def _prepare_questionnaires(records: list[dict]) -> list[tuple]:
    """Valida y prepara todo el lote antes de realizar escrituras."""
    if not isinstance(records, list):
        raise StorageError("El lote debe ser una lista")

    # Preparación completa antes de abrir una transacción.
    prepared = []
    seen_ids: set[int] = set()

    for record in records:
        if not isinstance(record, dict):
            raise StorageError("Estructura de cuestionario inválida")

        identifier = record.get("id")

        if type(identifier) is not int or not 0 < identifier <= 2**63 - 1:
            raise StorageError("Identificador de cuestionario inválido")

        if identifier in seen_ids:
            raise StorageError("Identificador repetido dentro del lote")

        seen_ids.add(identifier)

        raw_date = record.get("fecha")

        if not isinstance(raw_date, str):
            raise StorageError("Fecha de cuestionario inválida")

        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError:
            raise StorageError("Fecha de cuestionario inválida") from None

        if parsed_date.isoformat() != raw_date:
            raise StorageError("Fecha de cuestionario inválida")

        prepared.append(
            (
                identifier,
                parsed_date,
                _optional_text(record, "tipoDocumento"),
                _optional_text(record, "Documento"),
                _optional_text(record, "Sede"),
                record,
                content_hash(record),
            )
        )

    return prepared


def _insert_prepared(cur: psycopg.Cursor, prepared: list[tuple]) -> int:
    """Ejecuta inserciones; la transacción es responsabilidad del llamante."""
    inserted = 0

    for (
        identifier,
        parsed_date,
        tipo,
        documento,
        sede,
        record,
        digest,
    ) in prepared:
        cur.execute(
            """
            INSERT INTO staging.clisueno_questionaries
                (
                    id,
                    fecha,
                    tipo_documento,
                    documento,
                    sede,
                    datos,
                    hash_contenido
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            (
                identifier,
                parsed_date,
                tipo,
                documento,
                sede,
                Jsonb(record),
                digest,
            ),
        )

        if cur.fetchone() is not None:
            inserted += 1
            continue

        cur.execute(
            """
            SELECT hash_contenido
            FROM staging.clisueno_questionaries
            WHERE id = %s
            """,
            (identifier,),
        )

        existing = cur.fetchone()

        if existing is None or existing[0] != digest:
            raise StorageConflictError(
                "ID existente con contenido diferente o no verificable"
            )

    return inserted


def store_questionnaires_in_transaction(
    conn: psycopg.Connection, records: list[dict]
) -> int:
    """Inserta con una conexión existente, sin commit ni rollback propios.

    El llamante debe controlar la transacción que incluye la auditoría.
    """
    prepared = _prepare_questionnaires(records)
    try:
        with conn.cursor() as cur:
            return _insert_prepared(cur, prepared)
    except psycopg.Error as exc:
        raise StorageError("Error de persistencia PostgreSQL") from exc


def store_questionnaires(database_url: str, records: list[dict]) -> int:
    """API compatible: ejecuta una carga completa en su propia transacción."""
    if not isinstance(database_url, str) or not database_url:
        raise StorageError("No se ha configurado DATABASE_URL")
    prepared = _prepare_questionnaires(records)
    try:
        with (
            psycopg.connect(database_url) as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            return _insert_prepared(cur, prepared)
    except psycopg.Error as exc:
        raise StorageError("Error de persistencia PostgreSQL") from exc
