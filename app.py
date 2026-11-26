"""Interfaz del asistente "Personal Shopper" (Streamlit).

Ejecutar con:  streamlit run app.py

T-25: estructura de la pantalla (D-12 a D-14) y pestaña **Preguntar**
(RF-01, RF-08, RF-31, D-15).
T-26: reproductor de audio sin reproducción automática (RF-09, D-03), aviso
cuando no hay audio (RF-19, D-18) y botón de WhatsApp (D-15, RF-25).
T-27: pestaña **Estimar** (RF-13 a RF-16, D-16): tarjetas de rango, monto,
zona, primera compra y desglose con la leyenda, recalculado sin botón.
T-28: pestaña **Historial** (RF-17, RNF-15): todas las consultas de la
sesión, solo en memoria, de la más nueva a la más vieja.
T-29: etiqueta "DEMO" y franja del modo demostración (RF-20, D-18), y avisos
de error con forma de burbuja (RF-18, sección 7).

Decisiones de Yeimy (2026-11-25, T-25):
- Trato de "usted" en toda la app, también en el saludo.
- La pestaña Preguntar muestra solo la última pregunta y su respuesta; las
  anteriores irán en la pestaña Historial (T-28).

Decisiones de Yeimy (2026-11-25, T-26):
- Reproductor nativo ``st.audio`` (widget de Streamlit, D-17), con
  ``autoplay=False``.
- Sin información suficiente no se genera audio; se muestra el botón de
  WhatsApp, que abre el chat con un mensaje inicial (sin la pregunta).
- Las respuestas con dos partes (RF-25) llevan audio y botón de WhatsApp.

Decisiones de Yeimy (2026-11-25, T-27):
- El monto es un campo de texto ("30000", "30.000" o "₡30.000"), validado
  con ``validar_monto()`` (RF-16).
- El formulario empieza vacío: sin monto no se muestra el desglose ni un error.
- El monto se recalcula al presionar Enter o salir del campo; la zona y la
  casilla, al instante.

Decisiones de Yeimy (2026-11-25, T-28): ver ``src/historial.py``.

Decisiones de Yeimy (2026-11-26, T-29):
- Los errores del servicio se muestran en una burbuja de aviso, en el lugar
  de la respuesta.
- Los errores que mencionan WhatsApp llevan el botón "Escribir por WhatsApp".
- Si la base o la configuración fallan al abrir, se ven el encabezado, el
  aviso con el botón y el pie (con el teléfono de respaldo de la sección 7).

RF-31: mientras se procesa una pregunta, el botón Enviar, el campo y las
preguntas rápidas quedan desactivados. El clic solo guarda la pregunta en
``pendiente`` (callback); la siguiente ejecución dibuja los controles ya
desactivados, procesa y vuelve a dibujar la pantalla.
"""

from __future__ import annotations

import logging

import streamlit as st

from src import demo, estilos, historial
from src.asistente import responder
from src.base_conocimiento import cargar_base
from src.calculadora import (
    MENSAJE_SIN_FECHA,
    calcular_cuenta,
    formatear_colones,
    hoy_costa_rica,
    proxima_fecha_compra,
    zonas_para_formulario,
)
from src.config import cargar_config, registrar_faltantes
from src.errores import TELEFONO_WHATSAPP, ErrorAsistente, ErrorCuota, ErrorValidacion

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
    st.session_state.setdefault("historial", [])       # RF-17: solo en memoria (RNF-15)


def pedir(pregunta: str) -> None:
    """Callback de Enviar y de las preguntas rápidas: guarda la pregunta y bloquea los controles."""
    st.session_state.pendiente = pregunta
    st.session_state.procesando = True
    st.session_state.aviso_pregunta = None


def enviar_escrita() -> None:
    pedir(st.session_state.get("campo_pregunta", ""))


def guardar_en_historial(pregunta: str, resultado: dict | None) -> None:
    st.session_state.historial = historial.agregar(
        st.session_state.historial, historial.entrada(pregunta, resultado))


def procesar(base: dict, config) -> None:
    """Responde la pregunta pendiente (spec 4.2) y desbloquea los controles."""
    pregunta = st.session_state.pendiente or ""
    try:
        with st.spinner("Buscando la respuesta…"):
            resultado = responder(pregunta, base, config)
        st.session_state.ultima = {"pregunta": pregunta.strip(), "resultado": resultado, "error": None}
        guardar_en_historial(pregunta, resultado)
    except ErrorValidacion as error:
        st.session_state.aviso_pregunta = str(error)  # no se llamó a ninguna API
    except ErrorAsistente as error:
        logger.warning("No se pudo responder: %s", error.detalle_tecnico or type(error).__name__)
        if isinstance(error, ErrorCuota):  # sección 7: sugerencia para la dueña
            logger.warning("Sugerencia: para la demostración, active MODO_DEMO=true en .env")
        st.session_state.ultima = {"pregunta": pregunta.strip(), "resultado": None, "error": str(error)}
        guardar_en_historial(pregunta, None)  # sección 7: "sin respuesta"
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

def boton_whatsapp(telefono: str) -> None:
    enlace = estilos.enlace_whatsapp(telefono, estilos.MENSAJE_WHATSAPP)
    st.link_button(estilos.ETIQUETA_WHATSAPP, enlace, key="whatsapp", icon=":material/chat:")


def mostrar_aviso(mensaje: str, telefono: str) -> None:
    """Error con forma de burbuja y, si lo menciona, botón de WhatsApp (T-29)."""
    st.html(estilos.burbuja_aviso(mensaje))
    if estilos.aviso_lleva_whatsapp(mensaje):
        boton_whatsapp(telefono)


def mostrar_respuesta(r: dict, base: dict) -> None:
    """Burbuja con fuente y categoría, reproductor o aviso, y botón de WhatsApp."""
    st.html(estilos.burbuja_respuesta(r["respuesta"], r["fuentes"], r["categoria"]))
    if r.get("audio"):
        st.audio(r["audio"], format="audio/mpeg", autoplay=False)  # D-03: no suena solo
    elif r.get("aviso_audio"):
        st.html(estilos.aviso_audio(r["aviso_audio"]))  # RF-19, D-18
    if estilos.necesita_whatsapp(r):
        boton_whatsapp(demo.telefono_whatsapp(base))


def pestana_preguntar(base: dict, config) -> None:
    procesando = st.session_state.procesando
    ultima = st.session_state.ultima

    if ultima:
        st.html(estilos.burbuja_pregunta(ultima["pregunta"]))
        if ultima["error"]:
            mostrar_aviso(ultima["error"], demo.telefono_whatsapp(base))
        else:
            mostrar_respuesta(ultima["resultado"], base)
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
        boton.form_submit_button("Enviar", key="enviar", on_click=enviar_escrita,
                                 disabled=procesando, width="stretch")
    if st.session_state.aviso_pregunta:
        st.caption(f":red[{st.session_state.aviso_pregunta}]")

    if procesando:
        procesar(base, config)


def pestana_estimar(base: dict) -> None:
    """Calculadora de estimado (spec 4.3). No llama a ninguna API: funciona sin conexión."""
    tarifas = base["tarifas"]
    con_cargo = set(base["zonas_domicilio"]["con_cargo"])
    entrega = formatear_colones(tarifas["entrega_domicilio_con_cargo"])

    tarjetas = st.empty()  # se llena al final, ya con el rango aplicado
    monto = st.text_input("Monto aproximado de sus productos", key="monto",
                          placeholder="Por ejemplo: ₡30.000")
    zona = st.selectbox("¿Dónde recibe?", zonas_para_formulario(base), key="zona",
                        format_func=lambda z: f"{z} (+{entrega})" if z in con_cargo else z)
    primera = st.checkbox("Es mi primera compra", key="primera_compra")

    porcentaje = None
    if monto.strip():  # vacío: sin desglose ni error (decisión de Yeimy)
        try:
            cuenta = calcular_cuenta(monto, zona, primera, base)
        except ErrorValidacion as error:
            st.caption(f":red[{error}]")  # RF-16: sin cálculo
        else:
            porcentaje = cuenta["porcentaje_servicio"]
            st.html(estilos.desglose(cuenta))
    tarjetas.html(estilos.tarjetas_de_rango(tarifas, porcentaje))


def pestana_historial() -> None:
    """Todas las consultas de la sesión, de la más nueva a la más vieja (RF-17)."""
    consultas = st.session_state.historial
    if not consultas:
        st.html(estilos.historial_vacio())
    for consulta in consultas:
        st.html(estilos.consulta_historial(consulta))
        if consulta["audio"]:
            st.audio(consulta["audio"], format="audio/mpeg", autoplay=False)  # desde la memoria
    st.html(estilos.nota_historial())


def main() -> None:
    st.set_page_config(page_title="Tu Personal Shopper", page_icon="🛒", layout="centered")
    iniciar_estado()
    st.html(estilos.CSS)
    st.html(estilos.SCRIPT_IDIOMA, unsafe_allow_javascript=True)  # página en español, sin traducir

    try:
        config = cargar_config()
        base = cargar_base()
        telefono = demo.telefono_whatsapp(base)
    except ErrorAsistente as error:
        # Sección 7: la app no se cierra. Sin base no hay fechas ni calculadora:
        # encabezado, aviso con WhatsApp (teléfono de respaldo) y pie.
        logger.error(error.detalle_tecnico or type(error).__name__)
        st.html(estilos.encabezado())
        mostrar_aviso(str(error), TELEFONO_WHATSAPP)
        st.html(estilos.pie(TELEFONO_WHATSAPP))
        return
    avisar_faltantes_una_vez(config)
    st.html(estilos.encabezado(config.modo_demo))  # D-18: "DEMO" y franja en modo demo

    hoy = hoy_costa_rica()
    fechas = proxima_fecha_compra(hoy, base["calendario_compras"])
    st.html(estilos.tarjeta_proxima_compra(fechas, hoy, MENSAJE_SIN_FECHA))

    total = len(st.session_state.historial)
    preguntar, estimar, pestana_hist = st.tabs(
        [":material/chat: Preguntar", ":material/calculate: Estimar",
         f":material/history: Historial ({total})"]  # D-13: cuántas consultas hay
    )
    with preguntar:
        pestana_preguntar(base, config)
    with estimar:
        pestana_estimar(base)
    with pestana_hist:
        pestana_historial()

    st.html(estilos.pie(telefono))


main()
