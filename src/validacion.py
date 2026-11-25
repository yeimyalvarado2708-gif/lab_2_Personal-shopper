"""Validación de las entradas del usuario (RF-02, RF-16; spec 5.1 y 5.2).

Se ejecuta antes de cualquier cálculo o llamada a una API. Si la entrada no es
válida se lanza ``ErrorValidacion`` con el mensaje exacto del spec, listo para
mostrarse al cliente.
"""

from __future__ import annotations

import math
import re

from src.errores import ErrorValidacion

LARGO_MAXIMO_PREGUNTA = 500  # RF-02

MENSAJE_PREGUNTA_VACIA = "Escriba una pregunta antes de enviar."
MENSAJE_PREGUNTA_LARGA = "La pregunta es muy larga. Use máximo 500 caracteres."
MENSAJE_MONTO_INVALIDO = "Ingrese un monto válido mayor a cero."

# Formato costarricense con separador de miles: "30.000", "1.250.000", "30.000,50".
_MILES_CON_PUNTO = re.compile(r"^\d{1,3}(?:\.\d{3})+(?:,\d+)?$")
# Decimal con coma y sin miles: "1500,50".
_DECIMAL_CON_COMA = re.compile(r"^\d+,\d+$")


def validar_pregunta(texto: str | None) -> str:
    """Devuelve la pregunta sin espacios al inicio ni al final.

    Lanza ``ErrorValidacion`` si está vacía, tiene solo espacios o pasa de
    500 caracteres (contados después de quitar los espacios de los extremos).
    """
    limpio = (texto or "").strip()
    if not limpio:
        raise ErrorValidacion(MENSAJE_PREGUNTA_VACIA)
    if len(limpio) > LARGO_MAXIMO_PREGUNTA:
        raise ErrorValidacion(MENSAJE_PREGUNTA_LARGA)
    return limpio


def _texto_a_numero(texto: str) -> float:
    """Convierte el texto de un monto a número, aceptando el formato de Costa Rica.

    "30.000" se lee como treinta mil (no como 30,0), porque así se escriben
    los montos en colones. También acepta el símbolo ₡ y espacios.
    """
    limpio = texto.replace("₡", "").replace(" ", "").strip()
    if _MILES_CON_PUNTO.match(limpio):
        limpio = limpio.replace(".", "").replace(",", ".")
    elif _DECIMAL_CON_COMA.match(limpio):
        limpio = limpio.replace(",", ".")
    return float(limpio)  # ValueError si no es numérico


def validar_monto(valor: object) -> float:
    """Devuelve el monto como número mayor que 0.

    Acepta números (lo que entrega un campo numérico de Streamlit) o texto.
    Lanza ``ErrorValidacion`` si está vacío, no es numérico, es cero o negativo.
    """
    if valor is None or isinstance(valor, bool):
        raise ErrorValidacion(MENSAJE_MONTO_INVALIDO)

    if isinstance(valor, (int, float)):
        monto = float(valor)
    elif isinstance(valor, str):
        try:
            monto = _texto_a_numero(valor)
        except ValueError:
            raise ErrorValidacion(MENSAJE_MONTO_INVALIDO) from None
    else:
        raise ErrorValidacion(MENSAJE_MONTO_INVALIDO)

    if not math.isfinite(monto) or monto <= 0:
        raise ErrorValidacion(MENSAJE_MONTO_INVALIDO)
    return monto
