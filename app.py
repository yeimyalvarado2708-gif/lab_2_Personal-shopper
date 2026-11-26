"""Interfaz del asistente "Personal Shopper" (Streamlit).

Ejecutar con:  streamlit run app.py

T-25: estructura de la pantalla (D-12 a D-14) y pestaña **Preguntar**
(RF-01, RF-08, RF-31, D-15). Las pestañas Estimar e Historial, el reproductor
de audio, el banner de demo y el diseño final de los errores se agregan en
T-26 a T-29.

Decisiones de Yeimy (2026-11-25, T-25):
- Trato de "usted" en toda la app, también en el saludo.
- La pestaña Preguntar muestra solo la última pregunta y su respuesta; las
  anteriores irán en la pestaña Historial (T-28).

RF-31: mientras se procesa una pregunta, el botón Enviar, el campo y las
preguntas rápidas quedan desactivados. El clic solo guarda la pregunta en
``pendiente`` (callback); la siguiente ejecución dibuja los controles ya
desactivados, procesa y vuelve a dibujar la pantalla.
"""

from __future__ import annotations

import logging

import streamlit as st

from src import demo, estilos
from src.asistente import responder
from src.base_conocimiento import cargar_base
from src.calculadora import MENSAJE_SIN_FECHA, hoy_costa_rica, proxima_fecha_compra
from src.config import cargar_config, registrar_faltantes
from src.errores import ErrorAsistente, ErrorValidacion

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("personal_shopper")

# Preguntas rápidas de D-15: texto del botón → pregunta que se envía.
PREGUNTAS_RAPIDAS = {
    "¿Cuánto cobran?": "¿Cuánto cobran?",
    "¿Número de SINPE?": "¿A qué número hago el SINPE?",
    "¿Próxima compra?": "¿Cuándo es la próxima compra?",
}


# ---------- estado de la sesión ----------

def iniciar_estado() -> None:
    st.session_state.setdefault("procesando", False)   # RF-31
    st.session_state.setdefault("pendiente", None)     # pregunta por procesar
    st.session_state.setdefault("ultima", None)        # última pregunta y su resultado
    st.session_state.setdefault("aviso_pregunta", None)  # error de validación


def pedir(pregunta: str) -> None:
    """Callback de Enviar y de las preguntas rápidas: guarda la pregunta y bloquea los controles."""
    st.session_state.pendiente = pregunta
    st.session_state.procesando = True
    st.session_state.aviso_pregunta = None


def enviar_escrita() -> None:
    pedir(st.session_state.get("campo_pregunta", ""))


def procesar(base: dict, config) -> None:
    """Responde la pregunta pendiente (spec 4.2) y desbloquea los controles."""
    pregunta = st.session_state.pendiente or ""
    try:
        with st.spinner("Buscando la respuesta…"):
            resultado = responder(pregunta, base, config)
        st.session_state.ultima = {"pregunta": pregunta.strip(), "resultado": resultado, "error": None}
    except ErrorValidacion as error:
        st.session_state.aviso_pregunta = str(error)  # no se llamó a ninguna API
    except ErrorAsistente as error:
        logger.warning("No se pudo responder: %s", error.detalle_tecnico or type(error).__name__)
        st.session_state.ultima = {"pregunta": pregunta.strip(), "resultado": None, "error": str(error)}
    finally:
        st.session_state.pendiente = None
        st.session_state.procesando = False
    st.rerun()


@st.cache_resource
def avisar_faltantes_una_vez(_config) -> bool:
    """Escribe en la consola, una sola vez, qué claves faltan en .env (sin valores)."""
    registrar_faltantes(_config)
    return True


# ---------- pantalla ----------

def pestana_preguntar(base: dict, config) -> None:
    procesando = st.session_state.procesando
    ultima = st.session_state.ultima

    if ultima:
        st.html(estilos.burbuja_pregunta(ultima["pregunta"]))
        if ultima["error"]:
            st.error(ultima["error"])  # diseño final de los errores en T-29
        else:
            r = ultima["resultado"]
            st.html(estilos.burbuja_respuesta(r["respuesta"], r["fuentes"], r["categoria"]))
    else:
        st.html(estilos.saludo())

    with st.container(horizontal=True, gap="small"):
        for i, (etiqueta, pregunta) in enumerate(PREGUNTAS_RAPIDAS.items()):
            st.button(etiqueta, key=f"rapida_{i}", on_click=pedir, args=(pregunta,),
                      disabled=procesando)

    with st.form("form_pregunta", clear_on_submit=True, border=False):
        campo, boton = st.columns([5, 1.4], vertical_alignment="bottom")
        campo.text_input("Su pregunta", key="campo_pregunta", placeholder="Escriba su pregunta…",
                         label_visibility="collapsed", disabled=procesando)
        boton.form_submit_button("Enviar", on_click=enviar_escrita, disabled=procesando,
                                 width="stretch")
    if st.session_state.aviso_pregunta:
        st.caption(f":red[{st.session_state.aviso_pregunta}]")

    if procesando:
        procesar(base, config)


def main() -> None:
    st.set_page_config(page_title="Tu Personal Shopper", page_icon="🛒", layout="centered")
    iniciar_estado()
    st.html(estilos.CSS)
    st.html(estilos.encabezado())

    try:
        config = cargar_config()
        base = cargar_base()
    except ErrorAsistente as error:
        logger.error(error.detalle_tecnico or type(error).__name__)
        st.error(str(error))  # sección 7: la app no se cierra
        return
    avisar_faltantes_una_vez(config)

    hoy = hoy_costa_rica()
    fechas = proxima_fecha_compra(hoy, base["calendario_compras"])
    st.html(estilos.tarjeta_proxima_compra(fechas, hoy, MENSAJE_SIN_FECHA))

    preguntar, estimar, historial = st.tabs(
        [":material/chat: Preguntar", ":material/calculate: Estimar", ":material/history: Historial"]
    )
    with preguntar:
        pestana_preguntar(base, config)
    with estimar:
        st.html(estilos.proximamente())  # T-27
    with historial:
        st.html(estilos.proximamente())  # T-28

    st.html(estilos.pie(demo.telefono_whatsapp(base)))


main()
