"""Utilidades de texto compartidas por el chat y el audio.

``recortar()`` aplica la regla de RF-10 (spec 4.1). La usan ``asistente``
(texto en pantalla) y ``voz`` (protección de créditos, decisión de Yeimy en
T-23). Está en un módulo aparte para que ``voz`` no dependa de ``asistente``.
"""

from __future__ import annotations

import re

PUNTOS_SUSPENSIVOS = "…"
_FIN_DE_ORACION = re.compile(r"[.!?…]")


def recortar(texto: str, limite: int) -> tuple[str, bool]:
    """Recorta ``texto`` a ``limite`` caracteres en la última oración completa.

    Si no termina ninguna oración dentro del límite, corta en la última
    palabra completa y agrega "…" (decisión de Yeimy). Devuelve el texto y si
    se recortó.
    """
    texto = texto.strip()
    if len(texto) <= limite:
        return texto, False

    # Un punto cuenta como fin de oración solo si en el texto COMPLETO le
    # sigue un espacio o el final (así no se corta dentro de "₡15.000").
    ultimo_fin = 0
    for marca in _FIN_DE_ORACION.finditer(texto, 0, limite):
        siguiente = texto[marca.end():marca.end() + 1]
        if siguiente == "" or siguiente.isspace():
            ultimo_fin = marca.end()
    if ultimo_fin:
        return texto[:ultimo_fin].rstrip(), True

    espacio_para_texto = limite - len(PUNTOS_SUSPENSIVOS)
    corte = texto[:espacio_para_texto]
    if texto[espacio_para_texto:espacio_para_texto + 1].strip():  # cortó una palabra
        ultimo_espacio = corte.rfind(" ")
        if ultimo_espacio > 0:
            corte = corte[:ultimo_espacio]
    return corte.rstrip(" ,;:") + PUNTOS_SUSPENSIVOS, True
