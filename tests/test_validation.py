"""Contrato mínimo de datos sin utilización de información clínica real."""

from copy import deepcopy
from datetime import date

import pytest

from src.validation import QuestionnaireValidationError, validate_questionnaires

DAY = date(2026, 10, 1)


def sample(identifier=1):
    return {
        "id": identifier,
        "fecha": "2026-10-01",
        "Documento": "ficticio",
        "medicamentoDormir": [],
        "medicamentoToma": [{"nombre": "", "dosis": "", "para_cual": ""}],
        "pregunta_desconocida": "",
    }


def test_valid_batch_is_unchanged():
    batch = [sample()]
    original = deepcopy(batch)
    assert validate_questionnaires(batch, DAY, DAY) is batch
    assert batch == original


def test_empty_batch_allowed():
    assert validate_questionnaires([], DAY, DAY) == []


@pytest.mark.parametrize("identifier", [None, "", -1, 0, True, 2**63, 1.2])
def test_invalid_identifier(identifier):
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([sample(identifier)], DAY, DAY)


def test_repeated_id_is_rejected():
    with pytest.raises(QuestionnaireValidationError, match="duplicado"):
        validate_questionnaires([sample(), sample()], DAY, DAY)


@pytest.mark.parametrize("value", ["", None, "2026-02-30", "2026-10-02", "01/10/2026"])
def test_invalid_date(value):
    record = sample()
    record["fecha"] = value
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([record], DAY, DAY)


@pytest.mark.parametrize("field", ["medicamentoDormir", "medicamentoToma"])
def test_invalid_medication_list(field):
    record = sample()
    record[field] = "texto"
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([record], DAY, DAY)


def test_medication_with_missing_keys_rejected():
    record = sample()
    record["medicamentoToma"] = [{"nombre": "ficticio"}]
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([record], DAY, DAY)


def test_medication_non_object_rejected():
    record = sample()
    record["medicamentoDormir"] = ["ficticio"]
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([record], DAY, DAY)


def test_optional_responses_and_unknown_fields_are_kept():
    record = sample()
    record["medicamentoToma"] = []
    record["otra_pregunta"] = None
    assert validate_questionnaires([record], DAY, DAY)[0] == record


def test_invalid_batch_shape():
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires({"datos": []}, DAY, DAY)


def test_invalid_record_shape():
    with pytest.raises(QuestionnaireValidationError):
        validate_questionnaires([None], DAY, DAY)
