"""Audio de las respuestas con ElevenLabs.

T-22 (este archivo por ahora): ``normalizar_para_audio()`` prepara el texto
para la voz (RF-26). El texto en pantalla no cambia: solo cambia lo que se
envía a ElevenLabs.

T-23 agrega ``sintetizar()``: la llamada a ElevenLabs, la caché en
``cache_audio/``, el tiempo de espera y la traducción de errores.

Reglas, en este orden (spec 5.6.1 y decisiones de Yeimy del 2026-11-25):

1. Se quitan los símbolos que no se pronuncian: ``*``, ``#``, ``_``, ``` ` ``` y ``~``.
2. Teléfonos de 8 dígitos ("8888-0000", "8888 0000", "88880000") → dígito
   por dígito: "8 8 8 8, 0 0 0 0".
3. Montos → número sin separador de miles + "colones":
   "₡36.500" → "36500 colones"; "2.000 colones" → "2000 colones".
   Los céntimos se dejan con coma (decisión de Yeimy): "₡14.999,99" →
   "14999,99 colones".
4. ``%``, ``+`` y ``=`` → palabras (decisión de Yeimy): "15%" → "15 por ciento",
   " + " → " más ", " = " → " es igual a ". La voz multilingüe a veces los lee
   en inglés o se los salta.
5. Se juntan los espacios repetidos.
"""

from __future__ import annotations

import re

# Símbolos de formato (Markdown) que la voz no debe leer.
_SIMBOLOS_MUDOS = re.compile(r"[*#_`~]")

# Teléfono de Costa Rica: 8 dígitos, con guion, espacio o juntos. No debe ser
# parte de un número más largo ni de un monto ("₡88880000", "88880000 colones").
_TELEFONO = re.compile(
    r"(?<![\d.,₡])(?<!₡ )(\d{4})[-\s]?(\d{4})(?![\d]|[.,]\d)(?!\s*colones\b)",
    re.IGNORECASE,
)

# Número en formato de Costa Rica: miles con punto (o espacio fino) y hasta
# dos céntimos con coma. Mismo formato que reconoce asistente.py (RF-24).
_NUMERO = r"\d{1,3}(?:[.  ]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?"
_MONTO_CON_SIMBOLO = re.compile(rf"₡\s*({_NUMERO})(?:\s*colones\b)?", re.IGNORECASE)
_MONTO_CON_PALABRA = re.compile(rf"(?<![\d.,])({_NUMERO})\s*colones\b", re.IGNORECASE)

_PORCENTAJE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_MAS = re.compile(r"\s+\+\s+")
_IGUAL = re.compile(r"\s*=\s*")
_ESPACIOS = re.compile(r"[ \t  ]+")
_ESPACIO_ANTES_DE_PUNTUACION = re.compile(r" +([.,;:!?)])")


def _digito_por_digito(coincidencia: re.Match) -> str:
    primera, segunda = coincidencia.group(1), coincidencia.group(2)
    return f"{' '.join(primera)}, {' '.join(segunda)}"


def _sin_separador_de_miles(numero: str) -> str:
    """"36.500" → "36500"; "14.999,99" → "14999,99" (la coma decimal se queda)."""
    return re.sub(r"[.  ]", "", numero)


def _monto_en_colones(coincidencia: re.Match) -> str:
    return f"{_sin_separador_de_miles(coincidencia.group(1))} colones"


def normalizar_para_audio(texto: str) -> str:
    """Prepara el texto de la respuesta para que la voz lo lea bien (RF-26).

    >>> normalizar_para_audio("El total es ₡36.500.")
    'El total es 36500 colones.'
    >>> normalizar_para_audio("SINPE al 8888-0000")
    'SINPE al 8 8 8 8, 0 0 0 0'
    """
    resultado = _SIMBOLOS_MUDOS.sub("", texto)
    resultado = _TELEFONO.sub(_digito_por_digito, resultado)
    resultado = _MONTO_CON_SIMBOLO.sub(_monto_en_colones, resultado)
    resultado = _MONTO_CON_PALABRA.sub(_monto_en_colones, resultado)
    resultado = _PORCENTAJE.sub(r"\1 por ciento", resultado)
    resultado = _MAS.sub(" más ", resultado)
    resultado = _IGUAL.sub(" es igual a ", resultado)
    resultado = resultado.replace("%", " por ciento")
    resultado = _ESPACIOS.sub(" ", resultado)
    resultado = _ESPACIO_ANTES_DE_PUNTUACION.sub(r"\1", resultado)
    return resultado.strip()
