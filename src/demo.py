"""Modo demostración: respuestas simuladas por palabras clave (RF-20, RF-30; spec 5.7).

Con ``MODO_DEMO=true`` el asistente usa este módulo en lugar de Gemini:

- No llama a ninguna API (este módulo no importa Gemini ni ElevenLabs).
- Busca la FAQ cuyas ``palabras_clave`` mejor coinciden con la pregunta,
  sin distinguir mayúsculas ni tildes ("SINPE" = "sinpe"; "envio" = "envío").
- Devuelve el mismo formato que Gemini (spec 5.5), con el texto precedido por
  ``[RESPUESTA SIMULADA]``.
- Si ninguna FAQ coincide, devuelve ``informacion_suficiente: false`` con el
  mensaje fijo de RF-21.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from src.calculadora import MENSAJE_SIN_FECHA
from src.errores import ErrorBaseConocimiento

PREFIJO_SIMULADA = "[RESPUESTA SIMULADA]"

# La FAQ de "próxima fecha" se responde con las fechas calculadas en Python
# (D-08), con fuente CALENDARIO, igual que lo hará Gemini (spec 5.5).
ID_FAQ_PROXIMA_FECHA = "FAQ-09"
FUENTE_CALENDARIO = "CALENDARIO"

CATEGORIA_SIN_INFORMACION = "Sin información"

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos: "¿Envío?" → "envio" (RF-30).

    La ñ se conserva ("año" ≠ "ano").
    """
    texto = unicodedata.normalize("NFD", str(texto).lower())
    sin_tildes = "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn" or c == "̃"  # conserva la tilde de la ñ
    )
    sin_tildes = unicodedata.normalize("NFC", sin_tildes)
    solo_palabras = re.sub(r"[^\w]+", " ", sin_tildes)
    return " ".join(solo_palabras.split())


def telefono_whatsapp(base: dict) -> str:
    """El número de ``negocio.contacto_humano`` (por ejemplo "8888-0000")."""
    contacto = base.get("negocio", {}).get("contacto_humano", "")
    encontrado = re.search(r"\d{4}-\d{4}", contacto)
    if not encontrado:
        raise ErrorBaseConocimiento(
            detalle_tecnico="'negocio.contacto_humano' no tiene un número con formato 8888-0000."
        )
    return encontrado.group()


def mensaje_sin_informacion(base: dict) -> str:
    """Mensaje fijo de RF-21, con el número tomado de la base."""
    return (
        f"No tengo esa información. Escríbanos por WhatsApp al {telefono_whatsapp(base)} "
        "y con gusto le ayudamos."
    )


def fecha_en_palabras(iso: str) -> str:
    """"2026-11-26" → "jueves 26 de noviembre"."""
    dia = date.fromisoformat(iso)
    return f"{_DIAS[dia.weekday()]} {dia.day} de {_MESES[dia.month - 1]}"


def _singular(texto_normalizado: str) -> str:
    """Quita la "s" final de cada palabra de más de 3 letras: "bancos" → "banco".

    Se aplica igual a la pregunta y a las palabras clave, así que "bancos"
    coincide con "banco" y "días" con "días", sin necesidad de reglas de gramática.
    """
    return " ".join(
        p[:-1] if len(p) > 3 and p.endswith("s") else p for p in texto_normalizado.split()
    )


def puntaje(pregunta_normalizada: str, palabras_clave: list[str]) -> int:
    """Suma de las palabras clave que aparecen completas en la pregunta.

    No distingue singular de plural ("bancos" = "banco"). Una frase clave vale
    tantos puntos como palabras tiene ("cuánto cuesta" = 2), porque es más
    específica que una palabra suelta.
    """
    total = 0
    texto = f" {_singular(pregunta_normalizada)} "
    for clave in palabras_clave:
        clave_normalizada = _singular(normalizar(clave))
        if clave_normalizada and f" {clave_normalizada} " in texto:
            total += len(clave_normalizada.split())
    return total


def mejor_faq(pregunta: str, base: dict) -> dict | None:
    """La FAQ con más puntaje; en empate, la de menor posición en la base."""
    pregunta_normalizada = normalizar(pregunta)
    mejor, mejor_puntaje = None, 0
    for faq in base["preguntas"]:
        valor = puntaje(pregunta_normalizada, faq.get("palabras_clave", []))
        if valor > mejor_puntaje:
            mejor, mejor_puntaje = faq, valor
    return mejor


def _respuesta_calendario(fechas: dict) -> str:
    if not fechas or not fechas.get("proxima_compra"):
        return MENSAJE_SIN_FECHA
    texto = f"La próxima compra es el {fecha_en_palabras(fechas['proxima_compra'])}."
    if fechas.get("fecha_limite_lista"):
        texto += (
            f" Puede enviar su lista hasta el "
            f"{fecha_en_palabras(fechas['fecha_limite_lista'])}."
        )
    return texto


def responder(pregunta: str, base: dict, fechas: dict) -> dict:
    """Respuesta simulada con el formato de Gemini (spec 5.5 y 5.7).

    ``fechas`` es el resultado de ``calculadora.proxima_fecha_compra()``.
    """
    faq = mejor_faq(pregunta, base)

    if faq is None:
        return {
            "respuesta": f"{PREFIJO_SIMULADA} {mensaje_sin_informacion(base)}",
            "fuentes": [],
            "categoria": CATEGORIA_SIN_INFORMACION,
            "informacion_suficiente": False,
            "aclaracion_pendiente": False,
        }

    if faq["id"] == ID_FAQ_PROXIMA_FECHA:
        texto, fuentes = _respuesta_calendario(fechas), [FUENTE_CALENDARIO]
    else:
        texto, fuentes = faq["respuesta"], [faq["id"]]

    return {
        "respuesta": f"{PREFIJO_SIMULADA} {texto}",
        "fuentes": fuentes,
        "categoria": faq["categoria"],
        "informacion_suficiente": True,
        "aclaracion_pendiente": False,
    }
