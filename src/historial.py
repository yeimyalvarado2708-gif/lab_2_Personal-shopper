"""Historial de la sesión (RF-17, RNF-15; T-28).

El historial vive **solo en memoria** (``st.session_state`` en ``app.py``): no
se escribe en disco y se borra al cerrar o recargar la página (RNF-15). Este
módulo solo arma las entradas; no guarda nada.

Cada entrada tiene lo que pide RF-17: pregunta, respuesta, fuente, categoría,
hora y estado del audio. También guarda los bytes del audio, para volver a
escucharlo desde la memoria sin gastar créditos.

Decisiones de Yeimy (2026-11-25, T-28):
- Se muestran todas las consultas de la sesión, de la más nueva a la más vieja.
- Cada consulta muestra el estado del audio y, si lo tiene, su reproductor.
- La hora va en formato de 12 horas, en hora de Costa Rica ("10:47 p. m.").
- Las preguntas que no pasan la validación no se guardan (no son consultas).
- Un error del servicio se guarda como "Sin respuesta" (spec, sección 7).
"""

from __future__ import annotations

from datetime import datetime

from src.calculadora import ZONA_HORARIA_CR

SIN_RESPUESTA = "Sin respuesta"  # spec, sección 7

ESTADO_CON_AUDIO = "🔊 Con audio"
ESTADO_DEMO = "Modo demo: sin audio"
ESTADO_SIN_INFORMACION = "🔇 Sin audio (sin información)"
ESTADO_NO_DISPONIBLE = "🔇 Audio no disponible"
ESTADO_SIN_RESPUESTA = "🔇 Sin audio"


def hora_en_12(ahora: datetime | None = None) -> str:
    """Hora de Costa Rica en formato de 12 horas: "10:47 p. m." (RF-28)."""
    momento = (ahora or datetime.now(ZONA_HORARIA_CR)).astimezone(ZONA_HORARIA_CR)
    hora = momento.hour % 12 or 12
    sufijo = "a. m." if momento.hour < 12 else "p. m."
    return f"{hora}:{momento.minute:02d} {sufijo}"


def estado_audio(resultado: dict) -> str:
    """Estado del audio de una respuesta de ``asistente.responder()``."""
    if resultado.get("audio"):
        return ESTADO_CON_AUDIO
    if resultado.get("modo_demo"):
        return ESTADO_DEMO
    if not resultado.get("informacion_suficiente", True):
        return ESTADO_SIN_INFORMACION
    return ESTADO_NO_DISPONIBLE


def entrada(pregunta: str, resultado: dict | None, ahora: datetime | None = None) -> dict:
    """Una consulta para el historial. ``resultado`` es ``None`` si el servicio falló."""
    base = {"hora": hora_en_12(ahora), "pregunta": pregunta.strip()}
    if resultado is None:
        return {**base, "respuesta": SIN_RESPUESTA, "fuentes": [], "categoria": "",
                "estado_audio": ESTADO_SIN_RESPUESTA, "audio": None}
    return {
        **base,
        "respuesta": resultado["respuesta"],
        "fuentes": list(resultado["fuentes"]),
        "categoria": resultado["categoria"],
        "estado_audio": estado_audio(resultado),
        "audio": resultado.get("audio"),
    }


def agregar(historial: list[dict], nueva: dict) -> list[dict]:
    """Devuelve el historial con ``nueva`` al principio (de la más nueva a la más vieja)."""
    return [nueva, *historial]
