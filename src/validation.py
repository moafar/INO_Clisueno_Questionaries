"""Validación estructural de cuestionarios MediCloud sin alterar datos clínicos."""

from datetime import date

MEDICATION_FIELDS = {
    "medicamentoDormir": {"nombre", "dosis", "cada_cuanto", "ultima_dosis"},
    "medicamentoToma": {"nombre", "dosis", "para_cual"},
}


class QuestionnaireValidationError(ValueError):
    """Respuesta no apta para persistencia; no incluye datos clínicos."""


def validate_questionnaires(
    records: list[dict],
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Valida un lote completo y devuelve los registros originales.

    Rechaza todo el lote ante cualquier error para evitar cargas parciales.
    Los campos clínicos ajenos al contrato mínimo se conservan sin cambios.
    """
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError("El intervalo requiere fechas válidas")
    if start_date > end_date:
        raise ValueError("Intervalo de fechas invertido")
    if not isinstance(records, list):
        raise QuestionnaireValidationError("La respuesta no es una lista")

    seen_ids: set[int] = set()
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise QuestionnaireValidationError(
                f"Registro {position}: estructura inválida"
            )

        identifier = record.get("id")
        if (
            type(identifier) is not int
            or not 0 < identifier <= 2**63 - 1
        ):
            raise QuestionnaireValidationError(
                f"Registro {position}: identificador inválido"
            )
        if identifier in seen_ids:
            raise QuestionnaireValidationError(
                f"Registro {position}: identificador duplicado"
            )
        seen_ids.add(identifier)

        raw_date = record.get("fecha")
        if not isinstance(raw_date, str):
            raise QuestionnaireValidationError(
                f"Registro {position}: fecha inválida"
            )
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise QuestionnaireValidationError(
                f"Registro {position}: fecha inválida"
            ) from None
        if parsed_date.isoformat() != raw_date or not start_date <= parsed_date <= end_date:
            raise QuestionnaireValidationError(
                f"Registro {position}: fecha fuera de intervalo o formato inválido"
            )

        for field, expected_keys in MEDICATION_FIELDS.items():
            if field not in record:
                continue  # Contrato evolutivo: ausencia se vigilará como cambio de esquema.
            medications = record[field]
            if not isinstance(medications, list):
                raise QuestionnaireValidationError(
                    f"Registro {position}: lista de medicamentos inválida"
                )
            for medication in medications:
                if not isinstance(medication, dict):
                    raise QuestionnaireValidationError(
                        f"Registro {position}: elemento de medicamentos inválido"
                    )
                if not expected_keys.issubset(medication):
                    raise QuestionnaireValidationError(
                        f"Registro {position}: estructura de medicamentos incompleta"
                    )

    return records
