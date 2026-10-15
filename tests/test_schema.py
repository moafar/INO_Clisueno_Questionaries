"""Pruebas de detección de deriva de esquema con registros ficticios."""

import json

import pytest

from src.schema import compare_schema, load_reference


def test_reference_is_versioned():
    fields = load_reference()
    assert len(fields) == 179
    assert "id" in fields
    assert "fecha" in fields


def test_unchanged_schema():
    report = compare_schema([{"id": 1, "fecha": "2026-10-01"}], frozenset({"id", "fecha"}))
    assert not report.changed


def test_extra_fields_are_reported_without_values():
    report = compare_schema(
        [{"id": 1, "nuevo": "dato ficticio"}], frozenset({"id"})
    )
    assert report.new_fields == frozenset({"nuevo"})
    assert "dato ficticio" not in repr(report)


def test_missing_fields_are_reported():
    report = compare_schema([{"id": 1}], frozenset({"id", "fecha"}))
    assert report.missing_fields == frozenset({"fecha"})


def test_inconsistent_records():
    report = compare_schema(
        [{"id": 1}, {"id": 2, "otro": ""}], frozenset({"id"})
    )
    assert report.inconsistent_records == 1
    assert report.changed


def test_empty_batch_is_not_drift():
    assert not compare_schema([], frozenset({"id"})).changed


def test_invalid_reference_file(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"version": 1, "cantidad_campos": 2, "campos": ["id"]}))
    with pytest.raises(ValueError, match="referencia"):
        load_reference(path)
