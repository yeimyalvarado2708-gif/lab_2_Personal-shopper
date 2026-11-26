"""Pruebas de T-22: voz.normalizar_para_audio() (RF-26, spec 5.6.1).

Las pruebas de la llamada a ElevenLabs y de la caché se agregan en T-23.
Ninguna prueba llama a ElevenLabs.
"""

import re

import pytest

from src import asistente, demo
from src.base_conocimiento import cargar_base
from src.voz import normalizar_para_audio

BASE = cargar_base()


# ---------- los 4 casos de la sección 5.6.1 del spec ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("El total es ₡36.500.", "El total es 36500 colones."),
    ("Envío de ₡2.000", "Envío de 2000 colones"),
    ("SINPE al 8888-0000", "SINPE al 8 8 8 8, 0 0 0 0"),
    ("**Importante:** pague antes", "Importante: pague antes"),
])
def test_casos_del_spec(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


# ---------- montos ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("₡2000", "2000 colones"),
    ("₡ 2.000", "2000 colones"),
    ("₡500", "500 colones"),
    ("₡1.250.000", "1250000 colones"),
    ("2.000 colones", "2000 colones"),
    ("₡2.000 colones", "2000 colones"),           # no repite "colones"
    ("₡15.000 y ₡40.000", "15000 colones y 40000 colones"),
    ("(₡4.500)", "(4500 colones)"),
    ("₡40.000.", "40000 colones."),                # el punto final no es parte del monto
])
def test_montos_en_colones(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("₡14.999,99", "14999,99 colones"),
    ("₡30.000,50 en total", "30000,50 colones en total"),
])
def test_centimos_se_dejan_con_coma(entrada, esperado):
    """Decisión de Yeimy: los céntimos se leen con coma."""
    assert normalizar_para_audio(entrada) == esperado


# ---------- teléfonos ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("Al número 8888-0000.", "Al número 8 8 8 8, 0 0 0 0."),
    ("WhatsApp al 8888 0000", "WhatsApp al 8 8 8 8, 0 0 0 0"),
    ("WhatsApp al 88880000", "WhatsApp al 8 8 8 8, 0 0 0 0"),
    ("al 2710-1234 o al 8888-0000", "al 2 7 1 0, 1 2 3 4 o al 8 8 8 8, 0 0 0 0"),
])
def test_telefonos_digito_por_digito(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("₡88880000", "88880000 colones"),
    ("88880000 colones", "88880000 colones"),
    ("En 23 barrios", "En 23 barrios"),
    ("₡1.250.000", "1250000 colones"),
])
def test_montos_y_otros_numeros_no_se_leen_como_telefono(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


# ---------- símbolos (decisión de Yeimy: %, + y = en palabras) ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("20% si la factura", "20 por ciento si la factura"),
    ("del 10% al 20%", "del 10 por ciento al 20 por ciento"),
    ("un 12,5 %", "un 12,5 por ciento"),
    ("factura + cargo", "factura más cargo"),
    ("Total = factura", "Total es igual a factura"),
])
def test_porcentaje_mas_e_igual_en_palabras(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("# Horario", "Horario"),
    ("Lea _esto_ y `aquello`", "Lea esto y aquello"),
    ("**Sí**, entrego ~gratis~.", "Sí, entrego gratis."),
    ("Texto  con   espacios", "Texto con espacios"),
    ("  al inicio y al final  ", "al inicio y al final"),
])
def test_simbolos_mudos_y_espacios(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


def test_texto_sin_nada_que_cambiar_queda_igual():
    texto = "Se compra los martes y se entrega los viernes, en Guápiles."
    assert normalizar_para_audio(texto) == texto


def test_texto_vacio():
    assert normalizar_para_audio("") == ""


# ---------- textos reales del proyecto ----------

def test_ejemplo_de_faq03():
    faq03 = next(f for f in BASE["preguntas"] if f["id"] == "FAQ-03")
    audio = normalizar_para_audio(faq03["respuesta"])
    assert audio.startswith("Total es igual a factura de PriceSmart más cargo del servicio")
    assert ("factura de 30000 colones más 15 por ciento (4500 colones) "
            "es igual a 34500 colones") in audio
    assert "36500 colones." in audio


def test_mensaje_de_la_calculadora():
    audio = normalizar_para_audio(asistente.mensaje_calculadora(BASE))
    assert "del 10 por ciento al 20 por ciento" in audio
    assert "y 2000 colones si la entrega" in audio


def test_mensaje_sin_informacion():
    audio = normalizar_para_audio(demo.mensaje_sin_informacion(BASE))
    assert audio == ("No tengo esa información. Escríbanos por WhatsApp al "
                     "8 8 8 8, 0 0 0 0 y con gusto le ayudamos.")


@pytest.mark.parametrize("faq", BASE["preguntas"], ids=lambda f: f["id"])
def test_ninguna_respuesta_de_la_base_deja_simbolos_para_la_voz(faq):
    audio = normalizar_para_audio(faq["respuesta"])
    for simbolo in "₡%+=*#_`~":
        assert simbolo not in audio
    assert not re.search(r"\b\d{4}-\d{4}\b", audio)  # teléfonos ya separados
    assert not re.search(r"\d\.\d{3}", audio)         # sin separador de miles


def test_el_texto_original_no_cambia():
    """RF-26: el texto en pantalla no cambia; solo se crea uno nuevo para la voz."""
    original = "El total es ₡36.500, escriba al 8888-0000."
    copia = str(original)
    normalizar_para_audio(original)
    assert original == copia
