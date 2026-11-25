"""Lectura de la configuración desde ``.env`` (spec 6.2; RNF-01, RNF-11).

Reglas de seguridad:

- Las claves solo se leen de variables de entorno (archivo ``.env``).
- Ningún mensaje, registro ni ``repr`` muestra el valor de una clave: solo se
  dice si la variable está configurada o falta.

Uso desde la consola, para revisar el ``.env`` sin mostrar valores::

    python -m src.config
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from src.errores import (
    MENSAJE_NO_DISPONIBLE,
    MENSAJE_SOLO_TEXTO,
    ErrorConfiguracion,
)

logger = logging.getLogger("personal_shopper")

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_ENV = RAIZ_PROYECTO / ".env"

# Valores por defecto (spec, tabla de la sección 6.2).
POR_DEFECTO = {
    "GEMINI_MODEL": "gemini-3.5-flash-lite",
    "ELEVENLABS_MODEL": "eleven_multilingual_v2",
    "LIMITE_CARACTERES_RESPUESTA": "400",
    "TIEMPO_ESPERA_API": "20",
    "MODO_DEMO": "false",
}

# Variables cuyo valor nunca se muestra.
VARIABLES_SECRETAS = ("GEMINI_API_KEY", "ELEVENLABS_API_KEY")

_VERDADERO = {"true", "1", "si", "sí", "yes"}
_FALSO = {"false", "0", "no", ""}


@dataclass(frozen=True)
class Config:
    """Configuración ya leída y validada. Las claves no aparecen en ``repr``."""

    gemini_api_key: str = field(repr=False)
    gemini_model: str
    elevenlabs_api_key: str = field(repr=False)
    elevenlabs_voice_id: str
    elevenlabs_model: str
    limite_caracteres_respuesta: int
    tiempo_espera_api: int
    modo_demo: bool

    def faltantes_gemini(self) -> list[str]:
        """Nombres de las variables de Gemini que faltan (nunca sus valores)."""
        return [] if self.gemini_api_key else ["GEMINI_API_KEY"]

    def faltantes_elevenlabs(self) -> list[str]:
        """Nombres de las variables de ElevenLabs que faltan (nunca sus valores)."""
        faltan = []
        if not self.elevenlabs_api_key:
            faltan.append("ELEVENLABS_API_KEY")
        if not self.elevenlabs_voice_id:
            faltan.append("ELEVENLABS_VOICE_ID")
        return faltan

    def verificar_gemini(self) -> None:
        """Lanza ``ErrorConfiguracion`` si falta la clave de Gemini (spec, sección 7)."""
        faltan = self.faltantes_gemini()
        if faltan:
            raise ErrorConfiguracion(
                MENSAJE_NO_DISPONIBLE,
                detalle_tecnico=f"Falta {', '.join(faltan)} en .env",
            )

    def verificar_elevenlabs(self) -> None:
        """Lanza ``ErrorConfiguracion`` si falta la clave o la voz de ElevenLabs."""
        faltan = self.faltantes_elevenlabs()
        if faltan:
            raise ErrorConfiguracion(
                MENSAJE_SOLO_TEXTO,
                detalle_tecnico=f"Falta {', '.join(faltan)} en .env",
            )


def _leer(entorno: Mapping[str, str], nombre: str) -> str:
    valor = entorno.get(nombre)
    if valor is None or not valor.strip():
        valor = POR_DEFECTO.get(nombre, "")
    return valor.strip()


def _leer_entero(entorno: Mapping[str, str], nombre: str) -> int:
    texto = _leer(entorno, nombre)
    try:
        numero = int(texto)
    except ValueError:
        numero = 0
    if numero <= 0:
        raise ErrorConfiguracion(
            MENSAJE_NO_DISPONIBLE,
            detalle_tecnico=f"{nombre} debe ser un número entero mayor a cero en .env",
        )
    return numero


def _leer_booleano(entorno: Mapping[str, str], nombre: str) -> bool:
    texto = _leer(entorno, nombre).lower()
    if texto in _VERDADERO:
        return True
    if texto in _FALSO:
        return False
    raise ErrorConfiguracion(
        MENSAJE_NO_DISPONIBLE,
        detalle_tecnico=f"{nombre} debe ser true o false en .env",
    )


def cargar_config(
    entorno: Mapping[str, str] | None = None,
    ruta_env: Path = RUTA_ENV,
) -> Config:
    """Lee y valida la configuración.

    Si ``entorno`` es ``None``, carga ``ruta_env`` en ``os.environ`` (sin pisar
    variables que ya existan) y lee de ahí. Las pruebas pasan un diccionario
    en ``entorno`` para no depender del ``.env`` real.

    Las claves que faltan NO lanzan error aquí: así la calculadora y el modo
    demo funcionan sin claves. Se verifican con ``verificar_gemini()`` y
    ``verificar_elevenlabs()`` justo antes de llamar a cada API.

    Lanza ``ErrorConfiguracion`` si un valor numérico o ``MODO_DEMO`` es inválido.
    """
    if entorno is None:
        load_dotenv(ruta_env, override=False)
        entorno = os.environ

    return Config(
        gemini_api_key=_leer(entorno, "GEMINI_API_KEY"),
        gemini_model=_leer(entorno, "GEMINI_MODEL"),
        elevenlabs_api_key=_leer(entorno, "ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=_leer(entorno, "ELEVENLABS_VOICE_ID"),
        elevenlabs_model=_leer(entorno, "ELEVENLABS_MODEL"),
        limite_caracteres_respuesta=_leer_entero(entorno, "LIMITE_CARACTERES_RESPUESTA"),
        tiempo_espera_api=_leer_entero(entorno, "TIEMPO_ESPERA_API"),
        modo_demo=_leer_booleano(entorno, "MODO_DEMO"),
    )


def informe_config(config: Config) -> list[str]:
    """Líneas de estado para la consola. Nunca incluye el valor de las claves."""

    def estado(nombre: str, presente: bool) -> str:
        if presente:
            return f"  {nombre}: configurada"
        if config.modo_demo:
            return f"  {nombre}: vacía (no se necesita con MODO_DEMO=true)"
        return f"  {nombre}: FALTA en .env"

    return [
        f"MODO_DEMO: {'true' if config.modo_demo else 'false'}",
        estado("GEMINI_API_KEY", bool(config.gemini_api_key)),
        f"  GEMINI_MODEL: {config.gemini_model}",
        estado("ELEVENLABS_API_KEY", bool(config.elevenlabs_api_key)),
        estado("ELEVENLABS_VOICE_ID", bool(config.elevenlabs_voice_id)),
        f"  ELEVENLABS_MODEL: {config.elevenlabs_model}",
        f"  LIMITE_CARACTERES_RESPUESTA: {config.limite_caracteres_respuesta}",
        f"  TIEMPO_ESPERA_API: {config.tiempo_espera_api} s",
    ]


def registrar_faltantes(config: Config) -> list[str]:
    """Escribe en la consola qué variables faltan (sin valores) y las devuelve.

    Con ``MODO_DEMO=true`` no se necesitan claves, así que no avisa nada.
    """
    if config.modo_demo:
        return []
    faltan = config.faltantes_gemini() + config.faltantes_elevenlabs()
    for nombre in faltan:
        logger.warning("Falta %s en .env", nombre)
    return faltan


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        cfg = cargar_config()
    except ErrorConfiguracion as error:
        logger.error(error.detalle_tecnico)
        raise SystemExit(1)
    print(f"Archivo: {RUTA_ENV.name} ({'encontrado' if RUTA_ENV.exists() else 'NO encontrado'})")
    print("\n".join(informe_config(cfg)))
    registrar_faltantes(cfg)
