"""Pruebas de T-28: src/historial.py (RF-17, RNF-15)."""

from datetime import datetime, timezone

import pytest

from src import historial

UTC = timezone.utc


@pytest.mark.parametrize("utc, esperado", [
    (datetime(2026, 11, 26, 4, 47, tzinfo=UTC), "10:47 p. m."),   # Costa Rica es UTC-6
    (datetime(2026, 11, 25, 18, 5, tzinfo=UTC), "12:05 p. m."),
    (datetime(2026, 11, 25, 6, 5, tzinfo=UTC), "12:05 a. m."),
    (datetime(2026, 11, 25, 15, 0, tzinfo=UTC), "9:00 a. m."),
])
def test_hora_en_12_horas_de_costa_rica(utc, esperado):
    """Decisión de Yeimy: formato de 12 horas, en hora de Costa Rica (RF-28)."""
    assert historial.hora_en_12(utc) == esperado


RESULTADO = {"respuesta": "Al 8888-0000.", "fuentes": ["FAQ-14"], "categoria": "Pagos",
             "informacion_suficiente": True, "modo_demo": False, "audio": b"ID3", "aviso_audio": None}


@pytest.mark.parametrize("cambios, estado", [
    ({}, historial.ESTADO_CON_AUDIO),
    ({"audio": None, "modo_demo": True}, historial.ESTADO_DEMO),
    ({"audio": None, "informacion_suficiente": False}, historial.ESTADO_SIN_INFORMACION),
    ({"audio": None, "aviso_audio": "El audio no está disponible en este momento."},
     historial.ESTADO_NO_DISPONIBLE),
])
def test_estado_del_audio(cambios, estado):
    assert historial.estado_audio({**RESULTADO, **cambios}) == estado


def test_entrada_con_todo_lo_que_pide_rf17():
    e = historial.entrada("  ¿Cómo pago?  ", RESULTADO, datetime(2026, 11, 26, 4, 47, tzinfo=UTC))
    assert e == {"hora": "10:47 p. m.", "pregunta": "¿Cómo pago?", "respuesta": "Al 8888-0000.",
                 "fuentes": ["FAQ-14"], "categoria": "Pagos",
                 "estado_audio": historial.ESTADO_CON_AUDIO, "audio": b"ID3"}


def test_entrada_sin_respuesta_cuando_el_servicio_falla():
    e = historial.entrada("¿Cómo pago?", None)
    assert e["respuesta"] == "Sin respuesta"
    assert e["fuentes"] == [] and e["audio"] is None


def test_agregar_pone_la_mas_nueva_primero_y_no_cambia_la_lista_original():
    viejo = [{"pregunta": "1"}]
    nuevo = historial.agregar(viejo, {"pregunta": "2"})
    assert [e["pregunta"] for e in nuevo] == ["2", "1"]
    assert viejo == [{"pregunta": "1"}]
