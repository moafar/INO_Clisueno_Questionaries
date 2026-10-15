"""Pruebas del formateador JSON de la extracción diaria."""

import json
import logging
from datetime import datetime, timedelta

from src.daily import JsonFormatter


def crear_registro(mensaje="Extracción completada"):
    return logging.LogRecord(
        name="src.daily",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=mensaje,
        args=(),
        exc_info=None,
    )


def test_logging_json_valido():
    resultado = JsonFormatter().format(crear_registro())
    datos = json.loads(resultado)

    assert isinstance(datos, dict)


def test_logging_campos_obligatorios():
    datos = json.loads(JsonFormatter().format(crear_registro()))

    assert set(datos) == {
        "timestamp",
        "level",
        "logger",
        "event",
    }

    assert datos["level"] == "INFO"
    assert datos["logger"] == "src.daily"
    assert datos["event"] == "Extracción completada"


def test_logging_timestamp_utc():
    datos = json.loads(JsonFormatter().format(crear_registro()))

    fecha = datetime.fromisoformat(datos["timestamp"])

    assert fecha.tzinfo is not None
    assert fecha.utcoffset() == timedelta(0)


def test_logging_caracteres_especiales():
    mensaje = 'Extracción: "correcta", registros = 25'
    datos = json.loads(
        JsonFormatter().format(crear_registro(mensaje))
    )

    assert datos["event"] == mensaje


def test_logging_no_agrega_campos_sensibles():
    datos = json.loads(JsonFormatter().format(crear_registro()))

    assert "token" not in datos
    assert "password" not in datos
    assert "app_key" not in datos
    assert "patient_id" not in datos
