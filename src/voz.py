"""Audio de las respuestas con ElevenLabs (RF-09, RF-11, RF-19, RF-26, RNF-12).

- ``normalizar_para_audio()`` (T-22) prepara el texto para la voz (RF-26).
  El texto en pantalla no cambia: solo cambia lo que se envía a ElevenLabs.
- ``sintetizar()`` (T-23) genera el MP3: recorta, normaliza, busca en la
  caché ``cache_audio/`` y, si no está, llama a ElevenLabs y lo guarda.

Reglas de ``normalizar_para_audio()``, en este orden (spec 5.6.1 y decisiones
de Yeimy del 2026-11-25):

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

Decisiones de Yeimy para ``sintetizar()`` (2026-11-25, T-23):

- Sin reintentos automáticos del SDK (``max_retries=0``), igual que Gemini
  (ciclo C-02): ninguna espera pasa de los 20 s de RNF-12.
- MP3 estándar: 44,1 kHz y 128 kbps (``mp3_44100_128``). La calidad no
  cambia los créditos: ElevenLabs cobra por caracteres.
- Si llega un texto de más de ``LIMITE_CARACTERES_RESPUESTA``, se recorta con
  la regla de RF-10 (``texto.recortar``) y se devuelve ``recortado: True``.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

import httpx
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

from src.config import Config, cargar_config
from src.errores import (
    MENSAJE_AUDIO_NO_DISPONIBLE,
    MENSAJE_CUOTA_AUDIO,
    MENSAJE_SOLO_TEXTO,
    ErrorConexion,
    ErrorConfiguracion,
    ErrorCuota,
    ErrorServicio,
)
from src.texto import recortar

logger = logging.getLogger("personal_shopper")

CARPETA_CACHE = Path(__file__).resolve().parent.parent / "cache_audio"
FORMATO_AUDIO = "mp3_44100_128"  # decisión de Yeimy: MP3 estándar
# Decisión de Yeimy (T-23): sin reintentos del SDK. En la versión 2.79.0,
# ``convert()`` usa el camino de streaming, que no reintenta; el valor se fija
# igual para que siga así si el SDK cambia (lo verifica test_voz.py).
REINTENTOS_SDK = 0

# Códigos de error que ElevenLabs manda en ``detail.status``.
_ESTADOS_CUOTA = {"quota_exceeded"}
_ESTADOS_CLAVE = {"invalid_api_key", "missing_permissions", "needs_authorization"}
_ESTADOS_VOZ = {"voice_not_found", "voice_does_not_exist", "paid_plan_required", "payment_required"}
_ESTADOS_MODELO = {"model_not_found", "invalid_model_id"}

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


# ---------- sintetizar (T-23) ----------

def clave_cache(texto_final: str, voice_id: str, modelo: str) -> str:
    """SHA-256 de ``texto_final + voice_id + modelo`` (spec 5.6)."""
    return hashlib.sha256((texto_final + voice_id + modelo).encode("utf-8")).hexdigest()


def _leer_cache(ruta: Path) -> bytes | None:
    try:
        audio = ruta.read_bytes()
    except OSError:
        return None
    return audio or None  # un archivo vacío no sirve


def _guardar_cache(ruta: Path, audio: bytes) -> None:
    """Guarda el MP3. Si falla (disco lleno, permisos), solo se avisa en la consola:
    el cliente recibe su audio igual."""
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = ruta.with_suffix(".tmp")
        temporal.write_bytes(audio)
        temporal.replace(ruta)  # nunca queda un MP3 a medias en la caché
    except OSError as error:
        logger.warning("No se pudo guardar el audio en la caché: %s", type(error).__name__)


def crear_cliente(config: Config) -> ElevenLabs:
    """Cliente de ElevenLabs con el tiempo de espera de RNF-12."""
    config.verificar_elevenlabs()
    return ElevenLabs(api_key=config.elevenlabs_api_key, timeout=config.tiempo_espera_api)


def _estado_del_error(error: ApiError) -> str:
    cuerpo = error.body if isinstance(error.body, dict) else {}
    detalle = cuerpo.get("detail", cuerpo)
    if isinstance(detalle, dict):
        return str(detalle.get("status") or detalle.get("code") or "")
    return ""


def traducir_error_api(error: ApiError, config: Config) -> Exception:
    """Convierte un error de ElevenLabs en una excepción propia (spec, sección 7).

    El detalle técnico nombra variables, nunca valores de claves.
    """
    codigo = error.status_code or 0
    estado = _estado_del_error(error)
    origen = f"ElevenLabs respondió {codigo}" + (f" ({estado})" if estado else "")

    if estado in _ESTADOS_CUOTA:
        return ErrorCuota(MENSAJE_CUOTA_AUDIO, f"{origen}: créditos del mes agotados")
    if estado in _ESTADOS_VOZ:
        return ErrorConfiguracion(
            MENSAJE_SOLO_TEXTO,
            f"{origen}: ELEVENLABS_VOICE_ID ({config.elevenlabs_voice_id}) no existe en la "
            "cuenta o no se puede usar en el plan gratuito; use una voz premade",
        )
    if estado in _ESTADOS_MODELO:
        return ErrorConfiguracion(
            MENSAJE_SOLO_TEXTO,
            f"{origen}: ELEVENLABS_MODEL ({config.elevenlabs_model}) no existe o no está disponible",
        )
    if estado in _ESTADOS_CLAVE or codigo in (401, 403):
        return ErrorConfiguracion(
            MENSAJE_SOLO_TEXTO,
            f"{origen}: ELEVENLABS_API_KEY no es válida o no tiene permiso de texto a voz",
        )
    if codigo == 404:
        return ErrorConfiguracion(
            MENSAJE_SOLO_TEXTO,
            f"{origen}: revise ELEVENLABS_VOICE_ID y ELEVENLABS_MODEL",
        )
    return ErrorServicio(MENSAJE_AUDIO_NO_DISPONIBLE, f"{origen}: servicio no disponible")


def _pedir_audio(cliente: ElevenLabs, texto_final: str, config: Config) -> bytes:
    try:
        partes = cliente.text_to_speech.convert(
            config.elevenlabs_voice_id,
            text=texto_final,
            model_id=config.elevenlabs_model,
            output_format=FORMATO_AUDIO,
            request_options={
                "max_retries": REINTENTOS_SDK,
                "timeout_in_seconds": config.tiempo_espera_api,
            },
        )
        audio = b"".join(partes)  # la solicitud se hace al recorrer las partes
    except ApiError as error:
        raise traducir_error_api(error, config) from None
    except httpx.TransportError as error:  # sin conexión o tiempo agotado
        raise ErrorConexion(
            MENSAJE_AUDIO_NO_DISPONIBLE,
            f"Sin conexión con ElevenLabs o se agotó TIEMPO_ESPERA_API "
            f"({config.tiempo_espera_api} s): {type(error).__name__}",
        ) from None
    if not audio:
        raise ErrorServicio(MENSAJE_AUDIO_NO_DISPONIBLE, "ElevenLabs devolvió un audio vacío")
    return audio


def sintetizar(
    texto: str,
    config: Config | None = None,
    cliente: ElevenLabs | None = None,
    carpeta_cache: Path | None = None,
) -> dict:
    """Genera el MP3 de la respuesta (spec 5.6).

    1. Recorta a ``LIMITE_CARACTERES_RESPUESTA`` con la regla de RF-10.
    2. Prepara el texto para la voz (RF-26).
    3. Busca en la caché por SHA-256 de texto + voz + modelo (RF-11): si está,
       no llama a ElevenLabs ni gasta créditos, aunque falte la clave o no haya
       conexión (spec, sección 9).
    4. Si no está, llama a ElevenLabs y guarda el MP3.

    Devuelve ``{"audio": bytes, "desde_cache": bool, "recortado": bool}``.
    Lanza ``ErrorConfiguracion``, ``ErrorConexion``, ``ErrorCuota`` o
    ``ErrorServicio`` con los mensajes de la sección 7. La consola nunca
    registra el texto ni las claves.
    """
    config = config or cargar_config()
    carpeta = carpeta_cache or CARPETA_CACHE

    texto_recortado, recortado = recortar(texto, config.limite_caracteres_respuesta)
    texto_final = normalizar_para_audio(texto_recortado)
    if not texto_final:
        raise ErrorServicio(MENSAJE_AUDIO_NO_DISPONIBLE, "Texto vacío: no se genera audio")
    if not config.elevenlabs_voice_id:
        config.verificar_elevenlabs()  # sin voz no hay clave de caché

    ruta = carpeta / f"{clave_cache(texto_final, config.elevenlabs_voice_id, config.elevenlabs_model)}.mp3"
    audio = _leer_cache(ruta)
    if audio is not None:
        logger.info("Audio desde la caché (sin gastar créditos)")
        return {"audio": audio, "desde_cache": True, "recortado": recortado}

    cliente = cliente or crear_cliente(config)
    audio = _pedir_audio(cliente, texto_final, config)
    _guardar_cache(ruta, audio)
    logger.info("Audio generado con ElevenLabs: %d caracteres", len(texto_final))
    return {"audio": audio, "desde_cache": False, "recortado": recortado}
