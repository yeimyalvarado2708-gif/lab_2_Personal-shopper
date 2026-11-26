"""Pruebas de T-25: src/estilos.py (D-12 a D-15, D-17)."""

from datetime import date

import pytest

from src import estilos
from src.calculadora import MENSAJE_SIN_FECHA

ATAQUE = '<script>alert("x")</script><img src=x onerror=alert(1)>'
FECHAS = {"proxima_compra": "2026-11-26", "fecha_limite_lista": "2026-11-25"}


# ---------- D-17: todo texto del cliente o de Gemini se escapa ----------

def test_la_pregunta_se_escapa():
    html = estilos.burbuja_pregunta(ATAQUE)
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.parametrize("campo", ["respuesta", "fuente", "categoria"])
def test_la_respuesta_la_fuente_y_la_categoria_se_escapan(campo):
    datos = {"respuesta": "Hola.", "fuentes": ["FAQ-14"], "categoria": "Pagos"}
    if campo == "fuente":
        datos["fuentes"] = [ATAQUE]
    else:
        datos[campo] = ATAQUE
    html = estilos.burbuja_respuesta(**datos)
    assert "<script>" not in html and "<img" not in html


# ---------- RF-08: fuente y categoría ----------

def test_respuesta_con_fuente_y_categoria():
    html = estilos.burbuja_respuesta("Al 8888-0000.", ["FAQ-14"], "Pagos")
    assert "Fuente: FAQ-14" in html
    assert ">Pagos<" in html


def test_varias_fuentes_se_muestran_juntas():
    assert "Fuente: FAQ-03, FAQ-02" in estilos.burbuja_respuesta("x", ["FAQ-03", "FAQ-02"], "Tarifas")


def test_sin_fuentes_no_se_muestra_la_etiqueta_de_fuente():
    html = estilos.burbuja_respuesta("No tengo esa información.", [], "Sin información")
    assert "Fuente" not in html
    assert "Sin información" in html


# ---------- D-14: tarjeta de próxima compra ----------

def test_tarjeta_antes_de_la_fecha_limite():
    html = estilos.tarjeta_proxima_compra(FECHAS, date(2026, 11, 23), MENSAJE_SIN_FECHA)
    assert "Próxima compra: jueves 26 nov" in html
    assert "Envíe su lista hasta el miércoles 25" in html
    assert "¡Cierra hoy!" not in html


def test_tarjeta_el_dia_limite_muestra_cierra_hoy():
    html = estilos.tarjeta_proxima_compra(FECHAS, date(2026, 11, 25), MENSAJE_SIN_FECHA)
    assert "Envíe su lista hasta hoy, miércoles 25" in html
    assert "¡Cierra hoy!" in html


def test_tarjeta_sin_fecha_muestra_el_texto_de_rf29():
    html = estilos.tarjeta_proxima_compra({"proxima_compra": None, "fecha_limite_lista": None},
                                          date(2026, 11, 25), MENSAJE_SIN_FECHA)
    assert MENSAJE_SIN_FECHA in html
    assert "Próxima compra:" not in html and "¡Cierra hoy!" not in html


# ---------- textos y diseño ----------

def test_el_saludo_usa_usted():
    """Decisión de Yeimy (T-25): "usted" en toda la app."""
    assert "¿Necesita información de nuestro servicio?" in estilos.saludo()
    assert "Necesitas" not in estilos.saludo()


def test_pie_con_whatsapp_de_la_base():
    html = estilos.pie("8888-0000")
    assert "¡Yo te lo compro!" in html
    assert 'href="https://wa.me/50688880000"' in html


def test_el_css_usa_los_colores_las_letras_y_los_selectores_de_streamlit_167():
    css = estilos.CSS
    for color in ("#173C8F", "#0B2463", "#D81B6A", "#F9D423", "#EAF4FD"):
        assert color in css
    assert "Kalam" in css and "Baloo+2" in css
    assert '[data-testid="stTab"]' in css
    assert 'data-baseweb="tab"' not in css  # ese selector ya no existe en 1.67
    assert ".react-aria-SelectionIndicator { display: none; }" in css  # sin raya bajo la pestaña
    assert ".st-key-enviar button" in css  # Enviar en fucsia
    assert ".stApp { background: #EAF4FD; }" in css  # página celeste, app en tarjeta blanca
    assert "'Material Symbols Rounded' !important" in css  # los íconos no toman la letra Baloo 2
    assert "PriceSmart" not in css  # D-12: no se usa la marca de otra empresa


# ---------- T-26: WhatsApp y aviso de audio ----------

def test_enlace_de_whatsapp_con_mensaje_inicial():
    enlace = estilos.enlace_whatsapp("8888-0000", estilos.MENSAJE_WHATSAPP)
    assert enlace == ("https://wa.me/50688880000?text=Hola%2C%20tengo%20una%20consulta%20sobre"
                      "%20el%20servicio%20de%20Personal%20Shopper.")


def test_el_mensaje_de_whatsapp_no_lleva_la_pregunta_y_usa_usted():
    assert estilos.MENSAJE_WHATSAPP == "Hola, tengo una consulta sobre el servicio de Personal Shopper."


def test_el_aviso_de_audio_se_escapa():
    html = estilos.aviso_audio(ATAQUE)
    assert "<script>" not in html and "&lt;script&gt;" in html


@pytest.mark.parametrize("suficiente, aclaracion, esperado", [
    (True, False, False),   # respuesta normal: solo audio
    (False, False, True),   # RF-21: botón en lugar del audio
    (True, True, True),     # RF-25: audio y botón (decisión de Yeimy)
])
def test_cuando_se_muestra_el_boton_de_whatsapp(suficiente, aclaracion, esperado):
    resultado = {"informacion_suficiente": suficiente, "aclaracion_pendiente": aclaracion}
    assert estilos.necesita_whatsapp(resultado) is esperado

