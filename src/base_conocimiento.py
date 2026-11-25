"""Carga y validación de ``data/base_conocimiento.json`` (RF-03; spec, sección 8).

Si la base falta o está mal formada se lanza ``ErrorBaseConocimiento``:

- ``str(error)`` es el mensaje fijo para el cliente (sin archivos ni campos).
- ``error.detalle_tecnico`` dice qué archivo o campo falló, para la consola.

Las demás funciones del asistente reciben el ``dict`` que devuelve
``cargar_base()``, ya validado.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from src.errores import MENSAJE_NO_DISPONIBLE, ErrorBaseConocimiento

RUTA_BASE = Path(__file__).resolve().parent.parent / "data" / "base_conocimiento.json"

CAMPOS_PREGUNTA = ("id", "categoria", "pregunta", "respuesta")
SECCIONES_OBLIGATORIAS = ("tarifas", "zonas_domicilio", "calendario_compras")
_FORMATO_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _error(detalle: str) -> ErrorBaseConocimiento:
    return ErrorBaseConocimiento(MENSAJE_NO_DISPONIBLE, detalle_tecnico=detalle)


def validar_base(base: object) -> dict:
    """Valida la estructura de la base ya leída. Devuelve la misma base.

    Revisa (RF-03 y spec, sección 8):
    - que sea un objeto JSON con la lista ``preguntas`` (no vacía);
    - que cada pregunta tenga ``id``, ``categoria``, ``pregunta`` y ``respuesta``
      como textos no vacíos;
    - que no haya ``id`` repetidos;
    - que existan ``tarifas``, ``zonas_domicilio`` y ``calendario_compras``;
    - que las fechas canceladas tengan formato ``AAAA-MM-DD`` y sean fechas reales.
    """
    if not isinstance(base, dict):
        raise _error("La base de conocimiento debe ser un objeto JSON ({...}).")

    preguntas = base.get("preguntas")
    if not isinstance(preguntas, list) or not preguntas:
        raise _error("Falta la lista 'preguntas' o está vacía.")

    vistos: set[str] = set()
    for posicion, faq in enumerate(preguntas, start=1):
        if not isinstance(faq, dict):
            raise _error(f"La pregunta #{posicion} no es un objeto JSON.")
        nombre = faq.get("id") if isinstance(faq.get("id"), str) else f"#{posicion}"
        for campo in CAMPOS_PREGUNTA:
            valor = faq.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise _error(f"La pregunta {nombre} no tiene el campo '{campo}' o está vacío.")
        if faq["id"] in vistos:
            raise _error(f"El id '{faq['id']}' está repetido.")
        vistos.add(faq["id"])

    for seccion in SECCIONES_OBLIGATORIAS:
        if not isinstance(base.get(seccion), dict):
            raise _error(f"Falta la sección '{seccion}'.")

    canceladas = base["calendario_compras"].get("fechas_canceladas", [])
    if not isinstance(canceladas, list):
        raise _error("'calendario_compras.fechas_canceladas' debe ser una lista.")
    for fecha in canceladas:
        if not isinstance(fecha, str) or not _FORMATO_FECHA.match(fecha):
            raise _error(f"La fecha cancelada {fecha!r} no tiene el formato AAAA-MM-DD.")
        try:
            date.fromisoformat(fecha)
        except ValueError:
            raise _error(f"La fecha cancelada {fecha!r} no es una fecha real.") from None

    return base


def cargar_base(ruta: Path = RUTA_BASE) -> dict:
    """Lee el archivo JSON, lo valida y devuelve la base como ``dict``.

    Lanza ``ErrorBaseConocimiento`` si el archivo no existe, no es un JSON
    válido o no cumple la estructura de ``validar_base()``.
    """
    ruta = Path(ruta)
    try:
        texto = ruta.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise _error(f"No se encontró el archivo {ruta.name}.") from None
    except (OSError, UnicodeDecodeError) as error:
        raise _error(f"No se pudo leer {ruta.name}: {type(error).__name__}.") from None

    try:
        base = json.loads(texto)
    except json.JSONDecodeError as error:
        raise _error(
            f"{ruta.name} no es un JSON válido (línea {error.lineno}, columna {error.colno})."
        ) from None

    return validar_base(base)


def buscar_pregunta(base: dict, id_pregunta: str) -> dict | None:
    """Devuelve la FAQ con ese ``id`` (por ejemplo ``"FAQ-03"``), o ``None``."""
    for faq in base["preguntas"]:
        if faq["id"] == id_pregunta:
            return faq
    return None
