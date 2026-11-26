"""Pruebas de T-19: src/asistente.py (RF-06, RF-07, RF-10, RF-21, RF-24, RF-25).

Casos de la sección 10 del spec y decisiones de Yeimy (2026-11-25). Todas
usan mocks: ninguna llama a Gemini ni gasta cuota.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from src import asistente, gemini_client
from src.base_conocimiento import cargar_base
from src.config import cargar_config
from src.demo import PREFIJO_SIMULADA
from src.errores import ErrorConexion, ErrorValidacion

BASE = cargar_base()
LIMITE = 400
MENSAJE_SIN_INFO = (
    "No tengo esa información. Escríbanos por WhatsApp al 8888-0000 y con gusto le ayudamos."
)
ACLARACION = "Para lo demás, escríbanos por WhatsApp al 8888-0000."


def gemini(respuesta="Puede pagar por SINPE Móvil al 8888-0000.", fuentes=("FAQ-14",),
           categoria="Pagos", suficiente=True, aclaracion=False):
    """Una respuesta de Gemini con el formato de spec 5.5."""
    return {
        "respuesta": respuesta,
        "fuentes": list(fuentes),
        "categoria": categoria,
        "informacion_suficiente": suficiente,
        "aclaracion_pendiente": aclaracion,
    }


def controlar(resultado, pregunta="¿Cómo pago?", limite=LIMITE, prefijo=""):
    return asistente.aplicar_controles(resultado, BASE, pregunta, limite, prefijo)


# ---------- respuesta válida: no se toca ----------

def test_respuesta_valida_pasa_sin_cambios():
    final = controlar(gemini())
    assert final["respuesta"] == "Puede pagar por SINPE Móvil al 8888-0000."
    assert final["fuentes"] == ["FAQ-14"]
    assert final["categoria"] == "Pagos"
    assert final["informacion_suficiente"] is True
    assert final["recortado"] is False
    assert final["controles"] == []


# ---------- RF-07: fuentes ----------

def test_fuente_inexistente_se_descarta():
    final = controlar(gemini(fuentes=["FAQ-14", "FAQ-99"]))
    assert final["fuentes"] == ["FAQ-14"]
    assert any("FAQ-99" in c for c in final["controles"])


def test_fuentes_repetidas_se_muestran_una_vez():
    assert controlar(gemini(fuentes=["FAQ-14", "FAQ-14"]))["fuentes"] == ["FAQ-14"]


def test_calendario_es_una_fuente_valida():
    final = controlar(gemini("La próxima compra es el jueves 26 de noviembre.",
                             fuentes=["CALENDARIO"], categoria="Fechas"))
    assert final["fuentes"] == ["CALENDARIO"]
    assert final["informacion_suficiente"] is True


@pytest.mark.parametrize("fuentes", [[], ["FAQ-99"], ["faq-14"], ["Base de conocimiento"]])
def test_suficiente_sin_fuente_valida_da_el_mensaje_fijo(fuentes):
    final = controlar(gemini("Sí, entregamos en Limón centro.", fuentes=fuentes))
    assert final["respuesta"] == MENSAJE_SIN_INFO
    assert final["informacion_suficiente"] is False
    assert final["fuentes"] == []


# ---------- RF-21 y RF-06: sin información ----------

def test_insuficiente_descarta_el_texto_inventado():
    inventado = gemini("No vendemos ropa, pero en Limón centro la entrega cuesta ₡3.000.",
                       fuentes=["FAQ-06"], suficiente=False)
    final = controlar(inventado)
    assert final["respuesta"] == MENSAJE_SIN_INFO
    assert "₡3.000" not in final["respuesta"]
    assert final["fuentes"] == []
    assert final["categoria"] == "Sin información"
    assert final["aclaracion_pendiente"] is False


def test_el_numero_de_whatsapp_sale_de_la_base():
    otra_base = {**BASE, "negocio": {**BASE["negocio"], "contacto_humano": "WhatsApp 7777-1234"}}
    final = asistente.aplicar_controles(gemini(suficiente=False), otra_base, "¿?", LIMITE)
    assert "7777-1234" in final["respuesta"]


def test_respuesta_vacia_da_el_mensaje_fijo():
    assert controlar(gemini("   "))["respuesta"] == MENSAJE_SIN_INFO


# ---------- RF-24: montos y porcentajes ----------

@pytest.mark.parametrize("texto", [
    "La entrega cuesta ₡2.000.",
    "La entrega cuesta ₡2000.",
    "La entrega cuesta 2.000 colones.",
    "El cargo es 20% si la factura es menor a ₡15.000.",
    "Ejemplo: factura de ₡30.000 + 15% (₡4.500) = ₡34.500; con entrega en La Trocha, ₡36.500.",
])
def test_montos_de_la_base_se_aceptan_en_cualquier_formato(texto):
    final = controlar(gemini(texto, fuentes=["FAQ-03"], categoria="Tarifas"),
                      pregunta="¿Cómo se calcula el total?")
    assert final["respuesta"] == texto


@pytest.mark.parametrize("texto", [
    "Por esa compra pagaría ₡25.300.",
    "Su total es de 25300 colones.",
    "La entrega en Limón cuesta ₡3.000.",
    "El total sería ₡36.501.",
])
def test_monto_que_no_existe_da_el_mensaje_de_la_calculadora(texto):
    final = controlar(gemini(texto, fuentes=["FAQ-03"], categoria="Tarifas"),
                      pregunta="¿Cuánto se cobra?")
    assert final["respuesta"] == asistente.MENSAJE_CALCULADORA
    assert final["fuentes"] == ["FAQ-03"]
    assert any(c.startswith("RF-24") for c in final["controles"])


@pytest.mark.parametrize("texto", ["El cargo es 12% de la factura.", "Se cobra un 25 por ciento."])
def test_porcentaje_que_no_existe_da_el_mensaje_de_la_calculadora(texto):
    final = controlar(gemini(texto, fuentes=["FAQ-02"], categoria="Tarifas"),
                      pregunta="¿Cuánto cobran?")
    assert final["respuesta"] == asistente.MENSAJE_CALCULADORA


def test_el_telefono_y_las_fechas_no_cuentan_como_montos():
    texto = "Pague por SINPE al 8888-0000 antes del jueves 26 de noviembre de 2026."
    assert controlar(gemini(texto))["respuesta"] == texto


# Decisión de Yeimy: si el cliente escribe un monto, solo se permiten los montos
# fijos de tarifas. Cubre EV-29, EV-30 y EV-31 del conjunto de evaluación.

def test_ev29_el_ejemplo_de_faq03_no_pasa_si_el_cliente_pidio_ese_calculo():
    pregunta = "¿Cuánto pago en total por ₡30.000 de compra con entrega en La Trocha?"
    cita_del_ejemplo = gemini("Con una factura de ₡30.000 y entrega en La Trocha, son ₡36.500.",
                              fuentes=["FAQ-03"], categoria="Tarifas")
    final = controlar(cita_del_ejemplo, pregunta=pregunta)
    assert final["respuesta"] == asistente.MENSAJE_CALCULADORA
    assert "36.500" not in final["respuesta"]
    assert "calculadora" in final["respuesta"]


@pytest.mark.parametrize("pregunta", [
    "Si compro ₡22.000, ¿cuánto es el total?",
    "Tengo ₡100.000 en productos y vivo en Buenos Aires, ¿cuánto le deposito?",
    "Si gasto 30 mil, ¿cuánto pago?",
    "¿Cuánto pago por 22000 colones?",
])
def test_si_el_cliente_escribe_un_monto_no_se_repite_ni_se_calcula(pregunta):
    texto = "Para ₡22.000 el cargo es 15%, es decir ₡3.300."
    final = controlar(gemini(texto, fuentes=["FAQ-03"], categoria="Tarifas"), pregunta=pregunta)
    assert final["respuesta"] == asistente.MENSAJE_CALCULADORA


def test_si_el_cliente_escribe_un_monto_se_permiten_las_tarifas_fijas():
    texto = ("El cargo es 15% si la factura está entre ₡15.000 y ₡40.000, más ₡2.000 de "
             "entrega en La Trocha. Use la calculadora de estimado.")
    final = controlar(gemini(texto, fuentes=["FAQ-02", "FAQ-03"], categoria="Tarifas"),
                      pregunta="Si compro ₡22.000 con entrega en La Trocha, ¿cuánto pago?")
    assert final["respuesta"] == texto


def test_sin_monto_en_la_pregunta_el_ejemplo_de_faq03_si_se_puede_citar():
    texto = "Por ejemplo, factura de ₡30.000 + 15% (₡4.500) = ₡34.500."
    final = controlar(gemini(texto, fuentes=["FAQ-03"], categoria="Tarifas"),
                      pregunta="¿Cómo calculan el total?")
    assert final["respuesta"] == texto


# ---------- RF-25: preguntas con dos partes ----------

def test_aclaracion_pendiente_agrega_el_texto_fijo():
    final = controlar(gemini("Vamos a PriceSmart los jueves.", fuentes=["FAQ-08"],
                             categoria="Fechas", aclaracion=True))
    assert final["respuesta"] == f"Vamos a PriceSmart los jueves. {ACLARACION}"
    assert final["aclaracion_pendiente"] is True


def test_aclaracion_con_texto_largo_no_pasa_del_limite():
    largo = "Vamos a PriceSmart los jueves. " * 20
    final = controlar(gemini(largo, fuentes=["FAQ-08"], aclaracion=True))
    assert len(final["respuesta"]) <= LIMITE
    assert final["respuesta"].endswith(ACLARACION)
    assert final["recortado"] is True


def test_si_rf24_reemplaza_el_texto_no_se_agrega_la_aclaracion():
    final = controlar(gemini("El total es ₡25.300.", fuentes=["FAQ-03"], aclaracion=True),
                      pregunta="¿Cuánto cobran y dan factura?")
    assert final["respuesta"] == asistente.MENSAJE_CALCULADORA


# ---------- RF-10: recorte a 400 caracteres ----------

def test_respuesta_larga_se_recorta_en_la_ultima_oracion_completa():
    oraciones = "Esta es una oración completa de prueba. " * 15  # 600 caracteres
    final = controlar(gemini(oraciones))
    assert len(final["respuesta"]) <= LIMITE
    assert final["respuesta"].endswith("prueba.")
    assert final["recortado"] is True


def test_no_se_corta_dentro_de_un_monto():
    texto = "Primera oración corta. " + "x" * 360 + " vale ₡15.000 en total y algo más."
    recortado, _ = asistente.recortar(texto, 400)
    assert recortado == "Primera oración corta."


def test_sin_fin_de_oracion_se_corta_en_palabra_con_puntos_suspensivos():
    una_oracion = "palabra " * 80  # 640 caracteres, sin punto
    recortado, fue_recortado = asistente.recortar(una_oracion, 400)
    assert fue_recortado is True
    assert len(recortado) <= 400
    assert recortado.endswith("palabra…")


def test_respuesta_de_400_exactos_no_se_toca():
    texto = "a" * 399 + "."
    assert asistente.recortar(texto, 400) == (texto, False)


def test_el_limite_sale_de_la_configuracion():
    final = controlar(gemini("Una oración. " * 30), limite=100)
    assert len(final["respuesta"]) <= 100


# ---------- modo demo: el prefijo se conserva y cuenta en el límite ----------

def test_demo_con_respuesta_larga_conserva_el_prefijo_y_el_limite():
    larga = f"{PREFIJO_SIMULADA} " + "Esta es una oración de la base. " * 13
    final = controlar(gemini(larga), prefijo=PREFIJO_SIMULADA)
    assert final["respuesta"].startswith(PREFIJO_SIMULADA)
    assert len(final["respuesta"]) <= LIMITE


def test_demo_sin_informacion_conserva_el_prefijo():
    final = controlar(gemini(f"{PREFIJO_SIMULADA} texto", suficiente=False), prefijo=PREFIJO_SIMULADA)
    assert final["respuesta"] == f"{PREFIJO_SIMULADA} {MENSAJE_SIN_INFO}"


# ---------- responder(): el flujo completo (spec 4.2) ----------

def config(**cambios):
    return cargar_config(entorno={"GEMINI_API_KEY": "clave-de-prueba", "MODO_DEMO": "false", **cambios})


def test_responder_con_gemini_aplica_los_controles(monkeypatch):
    falso = MagicMock(return_value=gemini(fuentes=["FAQ-14", "FAQ-99"]))
    monkeypatch.setattr(gemini_client, "generar_respuesta", falso)
    final = asistente.responder("  ¿Cómo pago?  ", BASE, config(), hoy=date(2026, 11, 23))
    assert final["fuentes"] == ["FAQ-14"]
    assert final["modo_demo"] is False
    pregunta, _, fechas, *_ = falso.call_args.args
    assert pregunta == "¿Cómo pago?"  # ya validada y sin espacios
    assert fechas == {"proxima_compra": "2026-11-26", "fecha_limite_lista": "2026-11-25"}


def test_responder_en_modo_demo_no_llama_a_gemini(monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta",
                        MagicMock(side_effect=AssertionError("no debía llamar a Gemini")))
    final = asistente.responder("¿A qué número hago el SINPE?", BASE, config(MODO_DEMO="true"))
    assert final["respuesta"].startswith(PREFIJO_SIMULADA)
    assert final["fuentes"] == ["FAQ-14"]
    assert final["modo_demo"] is True


def test_responder_en_modo_demo_respeta_la_decision_de_montos():
    final = asistente.responder("Si compro ₡30.000 con entrega en La Trocha, ¿cuánto es el total?",
                                BASE, config(MODO_DEMO="true"))
    assert "36.500" not in final["respuesta"]


def test_responder_valida_la_pregunta_antes_de_llamar(monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta",
                        MagicMock(side_effect=AssertionError("no debía llamar a Gemini")))
    with pytest.raises(ErrorValidacion):
        asistente.responder("   ", BASE, config())


def test_responder_deja_pasar_los_errores_de_gemini(monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta", MagicMock(side_effect=ErrorConexion()))
    with pytest.raises(ErrorConexion):
        asistente.responder("¿Cómo pago?", BASE, config())


def test_los_controles_no_registran_la_pregunta(caplog, monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta",
                        MagicMock(return_value=gemini(fuentes=["FAQ-99"])))
    with caplog.at_level("INFO", logger="personal_shopper"):
        asistente.responder("Mi pregunta privada sobre pagos", BASE, config())
    assert "RF-07" in caplog.text
    assert "Mi pregunta privada" not in caplog.text  # RNF-15
