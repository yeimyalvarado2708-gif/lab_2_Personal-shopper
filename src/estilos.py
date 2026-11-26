"""CSS y HTML de la interfaz (D-12, D-13, D-14, D-15, D-17).

Aquí solo está lo que **se muestra**: encabezado, tarjeta de próxima compra,
saludo, burbujas del chat y pie. Todo lo que el cliente **usa** (campo de
pregunta, botones) son widgets de Streamlit en ``app.py`` (D-17).

**Todo texto del cliente o de Gemini pasa por ``html.escape()``** antes de
entrar al HTML (D-17): así una pregunta con código no se ejecuta en la página.

La referencia visual es ``docs/prototipo_interfaz.html``.

Selectores verificados en Streamlit 1.67 (T-25): las pestañas son
``[data-testid="stTab"]`` (la activa lleva ``aria-selected="true"`` y
``data-selected``; su raya inferior es ``.react-aria-SelectionIndicator`` y la
línea gris de la lista es el ``::after`` de ``[role="tablist"]``); la página es
``.stApp``; el contenedor principal es ``[data-testid="stMainBlockContainer"]``;
el campo de texto es ``[data-testid="stTextInputRootElement"]``; cada widget
con ``key`` lleva la clase ``st-key-<key>`` (los formularios no la llevan: el
botón Enviar tiene su propia ``key``).
"""

from __future__ import annotations

import html
import re
from datetime import date
from urllib.parse import quote

from src.calculadora import formatear_colones
from src.demo import _DIAS, _MESES

# Colores de D-12 (volante del emprendimiento). No se usan el logo ni la
# tipografía de PriceSmart.
AZUL = "#173C8F"
AZUL_OSCURO = "#0B2463"
FUCSIA = "#D81B6A"
VERDE = "#239B3E"
MORADO = "#6A2C9E"
AMARILLO = "#F9D423"
CELESTE = "#EAF4FD"
TEXTO = "#1F2A44"
GRIS = "#5B6680"

SALUDO = "¿Necesita información de nuestro servicio?"  # decisión de Yeimy: "usted" en todo
# Decisión de Yeimy (T-26): el botón de WhatsApp abre el chat con este texto
# ya escrito. No incluye la pregunta del cliente.
MENSAJE_WHATSAPP = "Hola, tengo una consulta sobre el servicio de Personal Shopper."
ETIQUETA_WHATSAPP = "Escribir por WhatsApp"

# RF-15: leyenda fija del estimado.
LEYENDA_ESTIMADO = (
    "Este es un estimado. El total exacto se lo envío el jueves desde PriceSmart, "
    "solo con los productos disponibles."
)
# Prototipo aprobado (D-16): aviso cuando se aplica la cortesía de primera compra.
TEXTO_CORTESIA = "Cortesía de bienvenida: sin cargo de servicio ni entrega"
# Colores de las tarjetas de rango, del menor al mayor monto (prototipo).
COLORES_RANGO = (FUCSIA, VERDE, MORADO)

# Decisión de Yeimy (ajuste de T-27): Streamlit marca la página como inglés
# (<html lang="en">) y Chrome la "traduce" al español, cambiando textos
# ("cargo" → "carga", montos sin ₡). Este script marca la página en español y
# le pide a Google que no la traduzca. Es la única excepción a D-17: no toca
# textos del cliente ni de Gemini, solo el idioma del documento.
SCRIPT_IDIOMA = """
<script>
(function () {
  var doc = window.parent && window.parent.document ? window.parent.document : document;
  var raiz = doc.documentElement;
  raiz.lang = "es";
  raiz.setAttribute("translate", "no");
  raiz.classList.add("notranslate");
  if (!doc.querySelector('meta[name="google"]')) {
    var meta = doc.createElement("meta");
    meta.name = "google";
    meta.content = "notranslate";
    doc.head.appendChild(meta);
  }
})();
</script>
"""

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kalam:wght@700&family=Baloo+2:wght@400;500;700&display=swap');

html, body, [class*="st-"], button, input, textarea {{
  font-family: 'Baloo 2', sans-serif;
}}
/* El contenedor del script de idioma no ocupa lugar (si no, deja una franja sobre el encabezado) */
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > script:only-child),
.stElementContainer:has(> [data-testid="stHtml"] > script:only-child) {{ display: none; }}
/* Los íconos de Streamlit conservan su propia fuente (si no, se ve la palabra "chat") */
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
/* Página celeste y la app en una tarjeta blanca, como el prototipo (ajuste de T-25) */
.stApp {{ background: {CELESTE}; }}
[data-testid="stMainBlockContainer"] {{
  max-width: 440px;
  background: #fff;
  border: 1px solid #D5E2F3;
  border-radius: 20px;
  overflow: hidden;
  padding: 0 14px;
  margin: 1.2rem auto;
  /* Que crezca con su contenido: si Streamlit la encoge al alto de la ventana,
     overflow: hidden corta lo que no cabe y no se puede bajar (ajuste de T-28). */
  flex-shrink: 0;
  height: auto;
}}
.ps-script {{ font-family: 'Kalam', cursive; font-weight: 700; }}

/* Encabezado y pie (D-13) */
.ps-encabezado {{ background: {AZUL}; margin: 0 -14px; padding: 14px 16px 12px; }}
.ps-encabezado .ps-titulo {{ margin: 0; color: #fff; font-size: 26px; line-height: 1.1; }}
.ps-encabezado .ps-lema {{ margin: 0; color: #fff; font-size: 13px; }}
.ps-encabezado .ps-lema span {{ background: {AMARILLO}; color: {AZUL}; padding: 0 6px; border-radius: 4px; font-weight: 700; }}
.ps-encabezado .ps-raya {{ height: 3px; width: 120px; background: {FUCSIA}; border-radius: 2px; margin-top: 6px; }}
.ps-pie {{ background: {AZUL}; margin: 0 -14px; display: flex; align-items: center;
  justify-content: center; gap: 10px; padding: 8px; }}
.ps-pie .ps-script {{ color: #fff; font-size: 22px; }}
.ps-pie a {{ background: {VERDE}; color: #fff !important; text-decoration: none; border-radius: 999px;
  padding: 2px 10px; font-size: 13px; font-weight: 500; }}

/* Tarjeta de próxima compra (D-14) */
.ps-tarjeta {{ display: flex; align-items: center; gap: 10px; background: {AMARILLO}; border-radius: 14px;
  padding: 8px 12px; color: {AZUL}; }}
.ps-tarjeta .ps-icono {{ font-size: 24px; }}
.ps-tarjeta .ps-fechas {{ flex: 1; line-height: 1.25; }}
.ps-tarjeta p {{ margin: 0; }}
.ps-tarjeta .ps-compra {{ font-weight: 700; font-size: 15px; }}
.ps-tarjeta .ps-limite {{ font-size: 13px; }}
.ps-tarjeta .ps-cierra {{ font-size: 11px; background: {FUCSIA}; color: #fff; padding: 2px 8px;
  border-radius: 999px; font-weight: 700; white-space: nowrap; }}

/* Pestañas (D-13): activa en azul oscuro con letra blanca; inactivas en blanco con letra gris */
[data-testid="stTabs"] [role="tablist"] {{ gap: 6px; }}
[data-testid="stTabs"] [role="tablist"]::after {{ display: none; }}
[data-testid="stTab"] .react-aria-SelectionIndicator {{ display: none; }}
[data-testid="stTab"] {{
  flex: 1; justify-content: center; background: #fff; border: 1.5px solid #D5E2F3 !important;
  border-radius: 999px; padding: 4px 8px; color: #7A86A0; height: auto;
}}
[data-testid="stTab"]:hover {{ background: #DCEAFB; color: {AZUL}; }}
[data-testid="stTab"][aria-selected="true"], [data-testid="stTab"][data-selected] {{ background: {AZUL_OSCURO}; border-color: {AZUL_OSCURO} !important; color: #fff; }}
[data-testid="stTab"] p {{ font-weight: 500; font-size: 14px; }}
[data-testid="stTab"][aria-selected="true"] p {{ font-weight: 700; }}

/* Saludo y burbujas (D-15) */
.ps-saludo {{ text-align: center; margin: 4px 0 10px; font-size: 20px; color: {AZUL}; line-height: 1.3; }}
.ps-fila-pregunta {{ display: flex; justify-content: flex-end; margin-bottom: 6px; }}
.ps-pregunta {{ background: {AZUL}; color: #fff; border-radius: 16px 16px 4px 16px; padding: 5px 12px;
  font-size: 15px; max-width: 85%; overflow-wrap: anywhere; }}
.ps-respuesta {{ background: {CELESTE}; border-radius: 16px 16px 16px 4px; padding: 10px 12px; }}
.ps-respuesta .ps-texto {{ margin: 0 0 6px; font-size: 15px; line-height: 1.5; overflow-wrap: anywhere; }}
.ps-etiquetas {{ display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }}
.ps-fuente {{ font-size: 11px; background: #fff; color: {AZUL}; border: 1px solid {AZUL};
  padding: 0 8px; border-radius: 999px; }}
.ps-categoria {{ font-size: 11px; background: {MORADO}; color: #fff; padding: 0 8px; border-radius: 999px; }}

/* Preguntas rápidas (D-15): botones de Streamlit con forma de chip */
[class*="st-key-rapida_"] button {{
  border: 1.5px solid {AZUL}; color: {AZUL}; border-radius: 999px; background: #fff;
  padding: 0 12px; min-height: 30px;
}}
[class*="st-key-rapida_"] button:hover {{ background: {CELESTE}; color: {AZUL}; border-color: {AZUL}; }}
[class*="st-key-rapida_"] button p {{ font-size: 13px; font-weight: 500; }}

/* Botón Enviar (fucsia) y campo de pregunta */
.st-key-enviar button {{
  background: {FUCSIA}; color: #fff; border: none; border-radius: 999px;
}}
.st-key-enviar button:hover, .st-key-enviar button:focus {{ background: #B8155A; color: #fff; border: none; }}
.st-key-enviar button:disabled {{ background: {FUCSIA}; color: #fff; opacity: .5; }}
.st-key-campo_pregunta [data-testid="stTextInputRootElement"] {{
  border-radius: 999px; border: 1.5px solid #C9D6EA; background: #fff;
}}

/* Audio y WhatsApp (T-26) */
[data-testid="stAudio"] {{ margin-top: -4px; }}
.ps-aviso-audio {{ margin: 0; font-size: 13px; color: {GRIS}; }}
.st-key-whatsapp a {{
  background: {VERDE}; color: #fff !important; border: none; border-radius: 999px;
  padding: 4px 14px; min-height: 0; text-decoration: none;
}}
.st-key-whatsapp a:hover {{ background: #1C7F33; color: #fff !important; }}
.st-key-whatsapp a p {{ font-size: 14px; font-weight: 500; }}

/* Pestaña Estimar (T-27, D-16) */
.ps-rangos {{ display: flex; gap: 6px; }}
.ps-rango {{ flex: 1; border-radius: 12px; padding: 6px 4px; text-align: center; border: 2px solid;
  background: #fff; transition: transform .15s; }}
.ps-rango p {{ margin: 0; font-weight: 700; }}
.ps-rango .ps-rango-nombre {{ font-size: 11px; }}
.ps-rango .ps-rango-porcentaje {{ font-size: 24px; line-height: 1.1; }}
.ps-rango.ps-activo {{ transform: scale(1.06); }}
.ps-rango.ps-activo p {{ color: #fff !important; }}
.ps-desglose {{ background: {CELESTE}; border-radius: 14px; padding: 10px 14px; }}
.ps-fila {{ display: flex; justify-content: space-between; font-size: 15px; padding: 2px 0; }}
.ps-separador {{ border-top: 2px dashed #B8C9E3; margin: 6px 0; }}
.ps-total {{ display: flex; justify-content: space-between; align-items: baseline; color: {AZUL}; }}
.ps-total .ps-script {{ font-size: 20px; }}
.ps-total .ps-total-monto {{ font-size: 28px; font-weight: 700; }}
.ps-cortesia {{ margin: 4px 0 0; font-size: 13px; color: {VERDE}; font-weight: 500; }}
.ps-leyenda {{ margin: 6px 0 0; font-size: 12px; color: {GRIS}; line-height: 1.4; }}

/* Pestaña Historial (T-28) */
.ps-historial-vacio {{ font-size: 15px; color: {GRIS}; text-align: center; margin: 6px 0; }}
.ps-consulta {{ border-bottom: 1px dashed #C9D6EA; padding: 6px 0 2px; }}
.ps-consulta .ps-meta {{ display: flex; justify-content: space-between; font-size: 12px; color: {GRIS}; }}
.ps-consulta .ps-consulta-pregunta {{ margin: 0; font-size: 15px; font-weight: 700; color: {AZUL}; overflow-wrap: anywhere; }}
.ps-consulta .ps-consulta-respuesta {{ margin: 0; font-size: 14px; color: {TEXTO}; overflow-wrap: anywhere; }}
.ps-consulta .ps-consulta-audio {{ margin: 2px 0 0; font-size: 12px; color: {GRIS}; }}
.ps-historial-nota {{ margin: 6px 0 0; font-size: 12px; color: {GRIS}; }}

.ps-pronto {{ font-size: 15px; color: {GRIS}; text-align: center; margin: 6px 0; }}
</style>
"""


def _e(texto: object) -> str:
    """Escapa texto para HTML (D-17)."""
    return html.escape(str(texto), quote=True)


def encabezado() -> str:
    """Encabezado de D-13. La etiqueta "DEMO" y la franja de RF-20 se agregan en T-29 (D-18)."""
    return (
        '<div class="ps-encabezado">'
        '<p class="ps-titulo ps-script">Tu Personal Shopper</p>'
        '<p class="ps-lema"><span>Ahorre tiempo y dinero</span> · Guápiles y alrededores</p>'
        '<div class="ps-raya"></div>'
        "</div>"
    )


def _fecha_corta(iso: str) -> str:
    """"2026-11-26" → "jueves 26 nov" (formato del prototipo)."""
    dia = date.fromisoformat(iso)
    return f"{_DIAS[dia.weekday()]} {dia.day} {_MESES[dia.month - 1][:3]}"


def _dia_y_numero(iso: str) -> str:
    """"2026-11-25" → "miércoles 25"."""
    dia = date.fromisoformat(iso)
    return f"{_DIAS[dia.weekday()]} {dia.day}"


def tarjeta_proxima_compra(fechas: dict, hoy: date, mensaje_sin_fecha: str) -> str:
    """Tarjeta amarilla de D-14, con las fechas de ``proxima_fecha_compra()``.

    Si hoy es la fecha límite, muestra "¡Cierra hoy!". Si no hay fecha
    (RF-29), muestra el texto fijo ``mensaje_sin_fecha``.
    """
    compra, limite = fechas.get("proxima_compra"), fechas.get("fecha_limite_lista")
    if not compra or not limite:
        cuerpo = f'<p class="ps-compra">{_e(mensaje_sin_fecha)}</p>'
        aviso = ""
    else:
        cierra_hoy = date.fromisoformat(limite) == hoy
        hasta = "hasta hoy, " if cierra_hoy else "hasta el "
        cuerpo = (
            f'<p class="ps-compra">Próxima compra: {_e(_fecha_corta(compra))}</p>'
            f'<p class="ps-limite">Envíe su lista {hasta}{_e(_dia_y_numero(limite))}</p>'
        )
        aviso = '<span class="ps-cierra">¡Cierra hoy!</span>' if cierra_hoy else ""
    return (
        '<div class="ps-tarjeta"><span class="ps-icono">🗓️</span>'
        f'<div class="ps-fechas">{cuerpo}</div>{aviso}</div>'
    )


def saludo() -> str:
    return f'<p class="ps-saludo ps-script">{_e(SALUDO)}</p>'


def burbuja_pregunta(pregunta: str) -> str:
    return f'<div class="ps-fila-pregunta"><span class="ps-pregunta">{_e(pregunta)}</span></div>'


def burbuja_respuesta(respuesta: str, fuentes: list[str], categoria: str) -> str:
    """Respuesta con su fuente y su categoría (RF-08).

    Sin fuentes (RF-21) no se muestra la etiqueta de fuente. El reproductor de
    audio y el botón de WhatsApp son widgets de ``app.py`` (T-26).
    """
    etiquetas = ""
    if fuentes:
        etiquetas += f'<span class="ps-fuente">Fuente: {_e(", ".join(fuentes))}</span>'
    if categoria:
        etiquetas += f'<span class="ps-categoria">{_e(categoria)}</span>'
    return (
        '<div class="ps-respuesta">'
        f'<p class="ps-texto">{_e(respuesta)}</p>'
        f'<div class="ps-etiquetas">{etiquetas}</div>'
        "</div>"
    )


def enlace_whatsapp(telefono: str, mensaje: str | None = None) -> str:
    """"8888-0000" → "https://wa.me/50688880000" (Costa Rica, código 506).

    Con ``mensaje``, el chat se abre con ese texto ya escrito (``?text=``).
    """
    digitos = re.sub(r"\D", "", telefono)
    enlace = f"https://wa.me/506{digitos}"
    return f"{enlace}?text={quote(mensaje)}" if mensaje else enlace


def aviso_audio(aviso: str) -> str:
    """Aviso en el lugar del reproductor (RF-19, D-18), con el texto escapado."""
    return f'<p class="ps-aviso-audio">🔇 {_e(aviso)}</p>'


def necesita_whatsapp(resultado: dict) -> bool:
    """Botón de WhatsApp: sin información (RF-21, D-15) o con dos partes (RF-25).

    Decisión de Yeimy (T-26): en las respuestas con dos partes se muestran el
    audio y el botón.
    """
    return not resultado["informacion_suficiente"] or bool(resultado.get("aclaracion_pendiente"))


def pie(telefono: str) -> str:
    """Pie de D-13 con "¡Yo te lo compro!" y el WhatsApp ficticio (RNF-03)."""
    return (
        '<div class="ps-pie"><span>🛒</span>'
        '<span class="ps-script">¡Yo te lo compro!</span>'
        f'<a href="{_e(enlace_whatsapp(telefono))}" target="_blank" rel="noopener">'
        f"WhatsApp {_e(telefono)}</a></div>"
    )


def proximamente() -> str:
    return '<p class="ps-pronto">Disponible pronto.</p>'


# ---------- pestaña Estimar (T-27) ----------

def nombres_de_rangos(tarifas: dict) -> list[str]:
    """Nombres de las tarjetas, armados con ``tarifas.rangos_servicio`` (no fijos en el código).

    Con las tarifas actuales: "Menos de ₡15.000", "₡15.000 a ₡40.000", "Más de ₡40.000".
    """
    rangos = tarifas["rangos_servicio"]
    nombres = []
    for i, rango in enumerate(rangos):
        if not rango.get("desde"):  # el primero: hasta el inicio del siguiente
            nombres.append(f"Menos de {formatear_colones(rangos[i + 1]['desde'])}")
        elif rango.get("hasta") is None:  # el último: desde el final del anterior
            nombres.append(f"Más de {formatear_colones(rangos[i - 1]['hasta'])}")
        else:
            nombres.append(f"{formatear_colones(rango['desde'])} a {formatear_colones(rango['hasta'])}")
    return nombres


def tarjetas_de_rango(tarifas: dict, porcentaje_activo: int | None) -> str:
    """Tres tarjetas de rango (D-16); la del rango aplicado se resalta en su color."""
    tarjetas = []
    rangos = tarifas["rangos_servicio"]
    for i, (rango, nombre) in enumerate(zip(rangos, nombres_de_rangos(tarifas))):
        color = COLORES_RANGO[i % len(COLORES_RANGO)]
        activo = rango["porcentaje"] == porcentaje_activo
        clase = "ps-rango ps-activo" if activo else "ps-rango"
        fondo = color if activo else "#fff"
        tarjetas.append(
            f'<div class="{clase}" style="border-color:{color};background:{fondo};color:{color};">'
            f'<p class="ps-rango-nombre">{_e(nombre.upper())}</p>'
            f'<p class="ps-rango-porcentaje">{_e(rango["porcentaje"])}%</p></div>'
        )
    return f'<div class="ps-rangos">{"".join(tarjetas)}</div>'


def desglose(cuenta: dict) -> str:
    """Desglose de RF-15 con la leyenda, a partir de ``calcular_cuenta()``."""
    filas = (
        ("Productos", cuenta["monto_productos"]),
        (f"Servicio ({cuenta['porcentaje_servicio']}%)", cuenta["cargo_servicio"]),
        ("Entrega", cuenta["costo_entrega"]),
    )
    html_filas = "".join(
        f'<div class="ps-fila"><span>{_e(nombre)}</span><span>{_e(formatear_colones(valor))}</span></div>'
        for nombre, valor in filas
    )
    cortesia = (f'<p class="ps-cortesia">🎁 {_e(TEXTO_CORTESIA)}</p>'
                if cuenta["cortesia_aplicada"] else "")
    return (
        f'<div class="ps-desglose">{html_filas}<div class="ps-separador"></div>'
        '<div class="ps-total"><span class="ps-script">Total estimado</span>'
        f'<span class="ps-total-monto">{_e(formatear_colones(cuenta["total_estimado"]))}</span></div>'
        f"{cortesia}</div>"
        f'<p class="ps-leyenda">{_e(LEYENDA_ESTIMADO)}</p>'
    )


# ---------- pestaña Historial (T-28) ----------

HISTORIAL_VACIO = "Sus preguntas de esta sesión aparecerán aquí."  # prototipo
NOTA_HISTORIAL = "Se borra al cerrar o recargar la página."  # prototipo y RNF-15


def historial_vacio() -> str:
    return f'<p class="ps-historial-vacio">{_e(HISTORIAL_VACIO)}</p>'


def consulta_historial(entrada: dict) -> str:
    """Una consulta del historial (RF-17): hora, categoría y fuente; pregunta; respuesta; audio."""
    detalle = " · ".join(filter(None, [entrada["categoria"], ", ".join(entrada["fuentes"])]))
    return (
        '<div class="ps-consulta">'
        f'<div class="ps-meta"><span>{_e(entrada["hora"])}</span><span>{_e(detalle)}</span></div>'
        f'<p class="ps-consulta-pregunta">{_e(entrada["pregunta"])}</p>'
        f'<p class="ps-consulta-respuesta">{_e(entrada["respuesta"])}</p>'
        f'<p class="ps-consulta-audio">{_e(entrada["estado_audio"])}</p>'
        "</div>"
    )


def nota_historial() -> str:
    return f'<p class="ps-historial-nota">{_e(NOTA_HISTORIAL)}</p>'

