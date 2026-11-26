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

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kalam:wght@700&family=Baloo+2:wght@400;500;700&display=swap');

html, body, [class*="st-"], button, input, textarea {{
  font-family: 'Baloo 2', sans-serif;
}}
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
    audio y el botón de WhatsApp se agregan en T-26.
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


def enlace_whatsapp(telefono: str) -> str:
    """"8888-0000" → "https://wa.me/50688880000" (Costa Rica, código 506)."""
    digitos = re.sub(r"\D", "", telefono)
    return f"https://wa.me/506{digitos}"


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
