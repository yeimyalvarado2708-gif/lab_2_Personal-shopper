"""Pruebas de T-15: src/demo.py (RF-20, RF-30; spec 5.7 y sección 10).

Casos del spec: modo demo sin llamadas a la API; coincidencia sin distinguir
mayúsculas ni tildes; sin coincidencia → información insuficiente.
"""

import socket
from datetime import date

import pytest

from src import demo
from src.base_conocimiento import cargar_base
from src.calculadora import MENSAJE_SIN_FECHA, proxima_fecha_compra
from src.errores import ErrorBaseConocimiento

BASE = cargar_base()
FECHAS = proxima_fecha_compra(date(2026, 11, 23), BASE["calendario_compras"])
CLAVES_FORMATO = {"respuesta", "fuentes", "categoria", "informacion_suficiente",
                  "aclaracion_pendiente"}


# ---------- sin llamadas a la API (RF-20) ----------

def test_demo_no_importa_los_sdk_de_las_api():
    codigo = open(demo.__file__, encoding="utf-8").read()
    for sdk in ("google", "genai", "elevenlabs", "requests", "httpx"):
        assert f"import {sdk}" not in codigo and f"from {sdk}" not in codigo


def test_responde_sin_red(monkeypatch):
    def sin_red(*args, **kwargs):
        raise AssertionError("El modo demo intentó conectarse a internet")

    monkeypatch.setattr(socket, "socket", sin_red)
    monkeypatch.setattr(socket, "create_connection", sin_red)
    resultado = demo.responder("¿A qué número hago el SINPE?", BASE, FECHAS)
    assert resultado["fuentes"] == ["FAQ-14"]


# ---------- formato de la respuesta (spec 5.5 y 5.7) ----------

def test_formato_igual_al_de_gemini():
    r = demo.responder("¿A qué número hago el SINPE?", BASE, FECHAS)
    assert set(r) == CLAVES_FORMATO
    assert r["respuesta"].startswith("[RESPUESTA SIMULADA] ")
    assert "8888-0000" in r["respuesta"]
    assert r["categoria"] == "Pagos"
    assert r["informacion_suficiente"] is True
    assert r["aclaracion_pendiente"] is False


def test_el_texto_es_el_de_la_faq():
    faq = next(f for f in BASE["preguntas"] if f["id"] == "FAQ-14")
    r = demo.responder("¿A qué número hago el SINPE?", BASE, FECHAS)
    assert r["respuesta"] == f"[RESPUESTA SIMULADA] {faq['respuesta']}"


# ---------- coincidencias ----------

@pytest.mark.parametrize(
    "pregunta, fuente",
    [
        ("¿Cuánto cobra por el servicio?", "FAQ-02"),
        ("¿Cuánto cuesta el envío a domicilio?", "FAQ-07"),
        ("¿Necesito membresía de PriceSmart?", "FAQ-20"),
        ("¿Qué medios de pago acepta?", "FAQ-13"),
        ("¿Con qué bancos puedo hacer transferencia?", "FAQ-15"),
        ("¿Hay un monto mínimo de compra?", "FAQ-22"),
    ],
)
def test_encuentra_la_faq_correcta(pregunta, fuente):
    assert demo.responder(pregunta, BASE, FECHAS)["fuentes"] == [fuente]


# ---------- sin distinguir mayúsculas ni tildes (RF-30) ----------

@pytest.mark.parametrize(
    "variante",
    ["¿A qué número hago el SINPE?", "a que numero hago el sinpe", "A QUÉ NÚMERO HAGO EL SINPE"],
)
def test_mayusculas_y_tildes_dan_lo_mismo(variante):
    assert demo.responder(variante, BASE, FECHAS)["fuentes"] == ["FAQ-14"]


def test_envio_sin_tilde_coincide_con_envio_con_tilde():
    con_tilde = demo.responder("¿Cuánto cuesta el envío?", BASE, FECHAS)
    sin_tilde = demo.responder("cuanto cuesta el envio", BASE, FECHAS)
    assert con_tilde["fuentes"] == sin_tilde["fuentes"] == ["FAQ-07"]


@pytest.mark.parametrize(
    "texto, esperado",
    [("¿Envío?", "envio"), ("SINPE Móvil", "sinpe movil"), ("  Más   de  ", "mas de"),
     ("Comisión, ¿cuánto?", "comision cuanto"), ("año", "año")],
)
def test_normalizar(texto, esperado):
    assert demo.normalizar(texto) == esperado


def test_solo_coinciden_palabras_completas():
    # "hay" es palabra clave de FAQ-11; no debe coincidir dentro de "playa".
    assert demo.puntaje(demo.normalizar("vivo cerca de la playa"), ["hay"]) == 0
    assert demo.puntaje(demo.normalizar("¿hay leche?"), ["hay"]) == 1


def test_singular_y_plural_dan_lo_mismo():
    # Caso encontrado al probar: "bancos" no coincidía con la clave "banco".
    assert demo.puntaje(demo.normalizar("¿Con qué bancos trabajan?"), ["banco"]) == 1
    assert demo.puntaje(demo.normalizar("¿Qué día van?"), ["días"]) == 1
    assert demo.puntaje(demo.normalizar("¿Qué días van?"), ["días"]) == 1


def test_frase_clave_vale_mas_que_palabra_suelta():
    assert demo.puntaje("cuanto cuesta", ["cuánto cuesta"]) == 2


# ---------- próxima fecha: fuente CALENDARIO ----------

def test_proxima_compra_usa_las_fechas_calculadas():
    r = demo.responder("¿Cuándo es la próxima compra?", BASE, FECHAS)
    assert r["fuentes"] == ["CALENDARIO"]
    assert r["categoria"] == "Fechas"
    assert r["respuesta"] == (
        "[RESPUESTA SIMULADA] La próxima compra es el jueves 26 de noviembre. "
        "Puede enviar su lista hasta el miércoles 25 de noviembre."
    )


def test_proxima_compra_sin_fecha_disponible_rf29():
    sin_fecha = {"proxima_compra": None, "fecha_limite_lista": None}
    r = demo.responder("¿Cuándo es la próxima compra?", BASE, sin_fecha)
    assert r["respuesta"] == f"[RESPUESTA SIMULADA] {MENSAJE_SIN_FECHA}"
    assert r["fuentes"] == ["CALENDARIO"]


def test_fecha_en_palabras():
    assert demo.fecha_en_palabras("2026-11-26") == "jueves 26 de noviembre"
    assert demo.fecha_en_palabras("2027-01-02") == "sábado 2 de enero"


# ---------- sin coincidencia → información insuficiente (RF-21) ----------

@pytest.mark.parametrize("pregunta", ["¿Venden boletos de avión?", "Hola", "xyz"])
def test_sin_coincidencia_informacion_insuficiente(pregunta):
    r = demo.responder(pregunta, BASE, FECHAS)
    assert set(r) == CLAVES_FORMATO
    assert r["informacion_suficiente"] is False
    assert r["fuentes"] == []
    assert r["categoria"] == "Sin información"
    assert r["respuesta"] == (
        "[RESPUESTA SIMULADA] No tengo esa información. Escríbanos por WhatsApp "
        "al 8888-0000 y con gusto le ayudamos."
    )


def test_numero_de_whatsapp_sale_de_la_base():
    base = {**BASE, "negocio": {"contacto_humano": "WhatsApp 7777-1234"}}
    assert "7777-1234" in demo.responder("xyz", base, FECHAS)["respuesta"]


def test_base_sin_numero_de_whatsapp():
    base = {**BASE, "negocio": {"contacto_humano": "por WhatsApp"}}
    with pytest.raises(ErrorBaseConocimiento):
        demo.responder("xyz", base, FECHAS)
