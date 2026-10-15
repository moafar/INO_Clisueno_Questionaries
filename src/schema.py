"""Detección no destructiva de cambios en los nombres de campos MediCloud."""

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "cuestionarios_v1.json"


@dataclass(frozen=True)
class SchemaReport:
    """Diferencias estructurales, sin valores ni identificadores clínicos."""

    new_fields: frozenset[str]
    missing_fields: frozenset[str]
    inconsistent_records: int

    @property
    def changed(self) -> bool:
        return bool(self.new_fields or self.missing_fields or self.inconsistent_records)


def load_reference(path: Path = DEFAULT_SCHEMA) -> frozenset[str]:
    """Carga la referencia versionada y verifica sus metadatos."""
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    fields = document.get("campos")
    if (
        document.get("version") != 1
        or not isinstance(fields, list)
        or not all(isinstance(field, str) and field for field in fields)
        or len(fields) != len(set(fields))
        or document.get("cantidad_campos") != len(fields)
    ):
        raise ValueError("El esquema de referencia es inválido")
    return frozenset(fields)


def compare_schema(
    records: list[dict], reference: frozenset[str]
) -> SchemaReport:
    """Compara nombres de campos sin modificar el lote ni registrar valores.

    Un lote vacío no permite inferir deriva: devuelve un informe sin cambios.
    """
    if not records:
        return SchemaReport(frozenset(), frozenset(), 0)

    shapes = [set(record) for record in records]
    all_fields = set.union(*shapes)
    common_fields = set.intersection(*shapes)
    baseline = shapes[0]

    return SchemaReport(
        new_fields=frozenset(all_fields - reference),
        missing_fields=frozenset(reference - common_fields),
        inconsistent_records=sum(shape != baseline for shape in shapes),
    )
