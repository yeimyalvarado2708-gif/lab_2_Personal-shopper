"""Pruebas de src/voz.py.

- T-22: ``normalizar_para_audio()`` (RF-26, spec 5.6.1).
- T-23: ``sintetizar()``: caché, llamada a ElevenLabs, tiempo de espera,
  errores y reintentos (RF-09, RF-11, RF-19, RNF-12).

Ninguna prueba llama a ElevenLabs ni gasta créditos: se usan mocks o un
transporte HTTP falso, y ``conftest.py`` bloquea la red real.
"""

import hashlib
import json
import logging
import re
from unittest.mock import MagicMock

import httpx
import pytest
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

from src import asistente, demo, voz
from src.base_conocimiento import cargar_base
from src.config import cargar_config
from src.errores import (
    MENSAJE_AUDIO_NO_DISPONIBLE,
    MENSAJE_CUOTA_AUDIO,
    MENSAJE_SOLO_TEXTO,
    ErrorConexion,
    ErrorConfiguracion,
    ErrorCuota,
    ErrorServicio,
)
from src.voz import normalizar_para_audio

BASE = cargar_base()


# ---------- los 4 casos de la sección 5.6.1 del spec ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("El total es ₡36.500.", "El total es 36500 colones."),
    ("Envío de ₡2.000", "Envío de 2000 colones"),
    ("SINPE al 8888-0000", "SINPE al 8 8 8 8, 0 0 0 0"),
    ("**Importante:** pague antes", "Importante: pague antes"),
])
def test_casos_del_spec(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


# ---------- montos ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("₡2000", "2000 colones"),
    ("₡ 2.000", "2000 colones"),
    ("₡500", "500 colones"),
    ("₡1.250.000", "1250000 colones"),
    ("2.000 colones", "2000 colones"),
    ("₡2.000 colones", "2000 colones"),           # no repite "colones"
    ("₡15.000 y ₡40.000", "15000 colones y 40000 colones"),
    ("(₡4.500)", "(4500 colones)"),
    ("₡40.000.", "40000 colones."),                # el punto final no es parte del monto
])
def test_montos_en_colones(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("₡14.999,99", "14999,99 colones"),
    ("₡30.000,50 en total", "30000,50 colones en total"),
])
def test_centimos_se_dejan_con_coma(entrada, esperado):
    """Decisión de Yeimy: los céntimos se leen con coma."""
    assert normalizar_para_audio(entrada) == esperado


# ---------- teléfonos ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("Al número 8888-0000.", "Al número 8 8 8 8, 0 0 0 0."),
    ("WhatsApp al 8888 0000", "WhatsApp al 8 8 8 8, 0 0 0 0"),
    ("WhatsApp al 88880000", "WhatsApp al 8 8 8 8, 0 0 0 0"),
    ("al 2710-1234 o al 8888-0000", "al 2 7 1 0, 1 2 3 4 o al 8 8 8 8, 0 0 0 0"),
])
def test_telefonos_digito_por_digito(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("₡88880000", "88880000 colones"),
    ("88880000 colones", "88880000 colones"),
    ("En 23 barrios", "En 23 barrios"),
    ("₡1.250.000", "1250000 colones"),
])
def test_montos_y_otros_numeros_no_se_leen_como_telefono(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


# ---------- símbolos (decisión de Yeimy: %, + y = en palabras) ----------

@pytest.mark.parametrize("entrada, esperado", [
    ("20% si la factura", "20 por ciento si la factura"),
    ("del 10% al 20%", "del 10 por ciento al 20 por ciento"),
    ("un 12,5 %", "un 12,5 por ciento"),
    ("factura + cargo", "factura más cargo"),
    ("Total = factura", "Total es igual a factura"),
])
def test_porcentaje_mas_e_igual_en_palabras(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


@pytest.mark.parametrize("entrada, esperado", [
    ("# Horario", "Horario"),
    ("Lea _esto_ y `aquello`", "Lea esto y aquello"),
    ("**Sí**, entrego ~gratis~.", "Sí, entrego gratis."),
    ("Texto  con   espacios", "Texto con espacios"),
    ("  al inicio y al final  ", "al inicio y al final"),
])
def test_simbolos_mudos_y_espacios(entrada, esperado):
    assert normalizar_para_audio(entrada) == esperado


def test_texto_sin_nada_que_cambiar_queda_igual():
    texto = "Se compra los martes y se entrega los viernes, en Guápiles."
    assert normalizar_para_audio(texto) == texto


def test_texto_vacio():
    assert normalizar_para_audio("") == ""


# ---------- textos reales del proyecto ----------

def test_ejemplo_de_faq03():
    faq03 = next(f for f in BASE["preguntas"] if f["id"] == "FAQ-03")
    audio = normalizar_para_audio(faq03["respuesta"])
    assert audio.startswith("Total es igual a factura de PriceSmart más cargo del servicio")
    assert ("factura de 30000 colones más 15 por ciento (4500 colones) "
            "es igual a 34500 colones") in audio
    assert "36500 colones." in audio


def test_mensaje_de_la_calculadora():
    audio = normalizar_para_audio(asistente.mensaje_calculadora(BASE))
    assert "del 10 por ciento al 20 por ciento" in audio
    assert "y 2000 colones si la entrega" in audio


def test_mensaje_sin_informacion():
    audio = normalizar_para_audio(demo.mensaje_sin_informacion(BASE))
    assert audio == ("No tengo esa información. Escríbanos por WhatsApp al "
                     "8 8 8 8, 0 0 0 0 y con gusto le ayudamos.")


@pytest.mark.parametrize("faq", BASE["preguntas"], ids=lambda f: f["id"])
def test_ninguna_respuesta_de_la_base_deja_simbolos_para_la_voz(faq):
    audio = normalizar_para_audio(faq["respuesta"])
    for simbolo in "₡%+=*#_`~":
        assert simbolo not in audio
    assert not re.search(r"\b\d{4}-\d{4}\b", audio)  # teléfonos ya separados
    assert not re.search(r"\d\.\d{3}", audio)         # sin separador de miles


def test_el_texto_original_no_cambia():
    """RF-26: el texto en pantalla no cambia; solo se crea uno nuevo para la voz."""
    original = "El total es ₡36.500, escriba al 8888-0000."
    copia = str(original)
    normalizar_para_audio(original)
    assert original == copia


# =====================================================================
# T-23: voz.sintetizar() — caché, ElevenLabs, tiempo de espera y errores.
# Todas con mocks o con un transporte HTTP falso: ninguna gasta créditos.
# =====================================================================

CLAVE = "clave-eleven-de-prueba-123"
VOZ = "voz-de-prueba"
MODELO = "eleven_multilingual_v2"
AUDIO = b"ID3-audio-falso"


def config_voz(**cambios):
    entorno = {
        "ELEVENLABS_API_KEY": CLAVE,
        "ELEVENLABS_VOICE_ID": VOZ,
        "MODO_DEMO": "false",
        **cambios,
    }
    return cargar_config(entorno=entorno)


def cliente_falso(audio=AUDIO):
    cliente = MagicMock()
    cliente.text_to_speech.convert.side_effect = lambda *a, **k: iter([audio[:3], audio[3:]])
    return cliente


def cliente_que_falla(error):
    cliente = MagicMock()
    cliente.text_to_speech.convert.side_effect = error
    return cliente


def error_api(codigo, estado=None):
    cuerpo = {"detail": {"status": estado, "message": "detalle"}} if estado else {"detail": "x"}
    return ApiError(status_code=codigo, headers={}, body=cuerpo)


def revisar_mensaje_seguro(error):
    """El cliente nunca ve claves, variables, códigos ni trazas (sección 7)."""
    mensaje = str(error)
    for prohibido in (CLAVE, "ELEVENLABS", "API", ".env", "401", "429", "500", "Traceback"):
        assert prohibido not in mensaje
    assert CLAVE not in error.detalle_tecnico


# ---------- audio generado y caché (RF-09, RF-11) ----------

def test_genera_audio_y_lo_guarda_en_la_cache(tmp_path):
    cliente = cliente_falso()
    resultado = voz.sintetizar("El total es ₡36.500.", config_voz(), cliente, tmp_path)

    assert resultado == {"audio": AUDIO, "desde_cache": False, "recortado": False}
    esperado = hashlib.sha256(("El total es 36500 colones." + VOZ + MODELO).encode()).hexdigest()
    assert (tmp_path / f"{esperado}.mp3").read_bytes() == AUDIO
    assert not list(tmp_path.glob("*.tmp"))


def test_llama_a_elevenlabs_con_texto_preparado_voz_modelo_y_formato(tmp_path):
    cliente = cliente_falso()
    voz.sintetizar("SINPE al 8888-0000", config_voz(), cliente, tmp_path)

    cliente.text_to_speech.convert.assert_called_once()
    args, kwargs = cliente.text_to_speech.convert.call_args
    assert args == (VOZ,)
    assert kwargs["text"] == "SINPE al 8 8 8 8, 0 0 0 0"  # RF-26
    assert kwargs["model_id"] == MODELO
    assert kwargs["output_format"] == "mp3_44100_128"  # decisión de Yeimy
    assert kwargs["request_options"] == {"max_retries": 0, "timeout_in_seconds": 20}


def test_audio_repetido_sale_de_la_cache_sin_llamar(tmp_path):
    config = config_voz()
    primero = cliente_falso()
    voz.sintetizar("Hola.", config, primero, tmp_path)

    segundo = cliente_falso()
    resultado = voz.sintetizar("Hola.", config, segundo, tmp_path)
    assert resultado == {"audio": AUDIO, "desde_cache": True, "recortado": False}
    segundo.text_to_speech.convert.assert_not_called()


def test_textos_que_se_leen_igual_comparten_audio(tmp_path):
    config = config_voz()
    voz.sintetizar("Cuesta ₡2.000.", config, cliente_falso(), tmp_path)
    otro = cliente_falso()
    assert voz.sintetizar("Cuesta 2.000 colones.", config, otro, tmp_path)["desde_cache"] is True
    otro.text_to_speech.convert.assert_not_called()


@pytest.mark.parametrize("cambio", [
    {"ELEVENLABS_VOICE_ID": "otra-voz"},
    {"ELEVENLABS_MODEL": "otro_modelo"},
])
def test_otra_voz_u_otro_modelo_no_usan_el_mismo_audio(tmp_path, cambio):
    voz.sintetizar("Hola.", config_voz(), cliente_falso(), tmp_path)
    otro = cliente_falso()
    assert voz.sintetizar("Hola.", config_voz(**cambio), otro, tmp_path)["desde_cache"] is False
    otro.text_to_speech.convert.assert_called_once()


def test_la_cache_funciona_sin_clave_y_sin_conexion(tmp_path):
    """Spec, sección 9: sin créditos o sin conexión, los audios en caché siguen sonando."""
    voz.sintetizar("Hola.", config_voz(), cliente_falso(), tmp_path)
    sin_clave = config_voz(ELEVENLABS_API_KEY="")
    sin_red = cliente_que_falla(httpx.ConnectError("sin red"))
    resultado = voz.sintetizar("Hola.", sin_clave, sin_red, tmp_path)
    assert resultado["desde_cache"] is True
    sin_red.text_to_speech.convert.assert_not_called()


def test_archivo_vacio_en_la_cache_se_ignora(tmp_path):
    clave = voz.clave_cache("Hola.", VOZ, MODELO)
    (tmp_path / f"{clave}.mp3").write_bytes(b"")
    cliente = cliente_falso()
    assert voz.sintetizar("Hola.", config_voz(), cliente, tmp_path)["desde_cache"] is False
    cliente.text_to_speech.convert.assert_called_once()


def test_si_no_se_puede_guardar_la_cache_el_audio_se_entrega_igual(tmp_path, caplog):
    carpeta = tmp_path / "no-es-carpeta"
    carpeta.write_text("soy un archivo")
    with caplog.at_level(logging.WARNING, logger="personal_shopper"):
        resultado = voz.sintetizar("Hola.", config_voz(), cliente_falso(), carpeta)
    assert resultado["audio"] == AUDIO
    assert "caché" in caplog.text


# ---------- recorte (decisión de Yeimy: regla de RF-10) ----------

def test_texto_largo_se_recorta_antes_de_gastar_creditos(tmp_path):
    texto = "Primera oración corta. " + "palabra " * 80
    cliente = cliente_falso()
    resultado = voz.sintetizar(texto, config_voz(), cliente, tmp_path)
    assert resultado["recortado"] is True
    enviado = cliente.text_to_speech.convert.call_args.kwargs["text"]
    assert enviado == "Primera oración corta."


def test_el_limite_sale_de_la_configuracion(tmp_path):
    cliente = cliente_falso()
    resultado = voz.sintetizar("Una. Dos. Tres.", config_voz(LIMITE_CARACTERES_RESPUESTA="9"),
                               cliente, tmp_path)
    assert resultado["recortado"] is True
    assert cliente.text_to_speech.convert.call_args.kwargs["text"] == "Una. Dos."


def test_texto_vacio_no_llama_a_elevenlabs(tmp_path):
    cliente = cliente_falso()
    with pytest.raises(ErrorServicio):
        voz.sintetizar("  ** ", config_voz(), cliente, tmp_path)
    cliente.text_to_speech.convert.assert_not_called()


# ---------- configuración faltante ----------

@pytest.mark.parametrize("falta, variable", [
    ({"ELEVENLABS_API_KEY": ""}, "ELEVENLABS_API_KEY"),
    ({"ELEVENLABS_VOICE_ID": ""}, "ELEVENLABS_VOICE_ID"),
])
def test_sin_clave_o_sin_voz_solo_texto_y_sin_llamar(tmp_path, falta, variable):
    with pytest.raises(ErrorConfiguracion) as error:
        voz.sintetizar("Hola.", config_voz(**falta), None, tmp_path)
    assert str(error.value) == MENSAJE_SOLO_TEXTO
    assert variable in error.value.detalle_tecnico
    revisar_mensaje_seguro(error.value)


# ---------- errores de ElevenLabs (sección 7) ----------

@pytest.mark.parametrize("codigo, estado, excepcion, mensaje, en_detalle", [
    (401, "quota_exceeded", ErrorCuota, MENSAJE_CUOTA_AUDIO, "créditos"),
    (401, "invalid_api_key", ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_API_KEY"),
    (401, None, ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_API_KEY"),
    (403, "missing_permissions", ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_API_KEY"),
    (400, "voice_not_found", ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_VOICE_ID"),
    (402, "paid_plan_required", ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_VOICE_ID"),
    (400, "model_not_found", ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_MODEL"),
    (404, None, ErrorConfiguracion, MENSAJE_SOLO_TEXTO, "ELEVENLABS_VOICE_ID"),
    (429, "too_many_concurrent_requests", ErrorServicio, MENSAJE_AUDIO_NO_DISPONIBLE, "429"),
    (500, None, ErrorServicio, MENSAJE_AUDIO_NO_DISPONIBLE, "500"),
    (503, None, ErrorServicio, MENSAJE_AUDIO_NO_DISPONIBLE, "503"),
    (422, None, ErrorServicio, MENSAJE_AUDIO_NO_DISPONIBLE, "422"),
])
def test_errores_de_elevenlabs_se_traducen(tmp_path, codigo, estado, excepcion, mensaje, en_detalle):
    with pytest.raises(excepcion) as error:
        voz.sintetizar("Hola.", config_voz(), cliente_que_falla(error_api(codigo, estado)), tmp_path)
    assert str(error.value) == mensaje
    assert en_detalle in error.value.detalle_tecnico
    revisar_mensaje_seguro(error.value)
    assert not list(tmp_path.glob("*.mp3"))  # un error no deja nada en la caché


@pytest.mark.parametrize("falla", [
    httpx.ConnectError("sin red"),
    httpx.ReadTimeout("se agotó el tiempo"),
    httpx.ConnectTimeout("se agotó el tiempo"),
])
def test_sin_conexion_o_tiempo_agotado_es_error_de_conexion(tmp_path, falla):
    with pytest.raises(ErrorConexion) as error:
        voz.sintetizar("Hola.", config_voz(), cliente_que_falla(falla), tmp_path)
    assert str(error.value) == MENSAJE_AUDIO_NO_DISPONIBLE
    assert "TIEMPO_ESPERA_API" in error.value.detalle_tecnico
    revisar_mensaje_seguro(error.value)


def test_audio_vacio_es_error_de_servicio(tmp_path):
    with pytest.raises(ErrorServicio):
        voz.sintetizar("Hola.", config_voz(), cliente_falso(audio=b""), tmp_path)
    assert not list(tmp_path.glob("*.mp3"))


def test_la_consola_no_registra_el_texto_ni_la_clave(tmp_path, caplog):
    texto = "Texto privado con ₡36.500."
    with caplog.at_level(logging.DEBUG, logger="personal_shopper"):
        voz.sintetizar(texto, config_voz(), cliente_falso(), tmp_path)
        voz.sintetizar(texto, config_voz(), cliente_falso(), tmp_path)
        with pytest.raises(ErrorCuota):
            voz.sintetizar("Otro.", config_voz(),
                           cliente_que_falla(error_api(401, "quota_exceeded")), tmp_path)
    assert "privado" not in caplog.text and "36500" not in caplog.text
    assert CLAVE not in caplog.text


# ---------- SDK real con un transporte HTTP falso ----------

def cliente_http(respuestas, solicitudes):
    """Un ElevenLabs real cuyo HTTP responde con ``respuestas`` (en orden), sin red."""
    def manejar(request):
        solicitudes.append(request)
        respuesta = respuestas[min(len(solicitudes), len(respuestas)) - 1]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    transporte = httpx.Client(transport=httpx.MockTransport(manejar))
    return ElevenLabs(api_key=CLAVE, httpx_client=transporte)


def test_sdk_real_envia_la_solicitud_correcta(tmp_path):
    solicitudes = []
    cliente = cliente_http([httpx.Response(200, content=AUDIO)], solicitudes)
    resultado = voz.sintetizar("Cuesta ₡2.000.", config_voz(), cliente, tmp_path)

    assert resultado["audio"] == AUDIO
    assert len(solicitudes) == 1
    pedido = solicitudes[0]
    assert pedido.url.path == f"/v1/text-to-speech/{VOZ}"
    assert pedido.url.params["output_format"] == "mp3_44100_128"
    cuerpo = json.loads(pedido.content)
    assert cuerpo["text"] == "Cuesta 2000 colones."
    assert cuerpo["model_id"] == MODELO


@pytest.mark.parametrize("codigo", [429, 500, 502, 503, 504])
def test_sdk_real_hace_una_sola_solicitud_sin_reintentos(tmp_path, codigo):
    """Decisión de Yeimy: sin reintentos. Se cuentan las solicitudes HTTP reales."""
    solicitudes = []
    cliente = cliente_http([httpx.Response(codigo, json={"detail": "x"})] * 3, solicitudes)
    with pytest.raises(ErrorServicio):
        voz.sintetizar("Hola.", config_voz(), cliente, tmp_path)
    assert len(solicitudes) == 1


def test_sdk_real_creditos_agotados(tmp_path):
    solicitudes = []
    cuerpo = {"detail": {"status": "quota_exceeded", "message": "This request exceeds your quota."}}
    cliente = cliente_http([httpx.Response(401, json=cuerpo)], solicitudes)
    with pytest.raises(ErrorCuota) as error:
        voz.sintetizar("Hola.", config_voz(), cliente, tmp_path)
    assert str(error.value) == MENSAJE_CUOTA_AUDIO


def test_sdk_real_tiempo_agotado(tmp_path):
    solicitudes = []
    cliente = cliente_http([httpx.ReadTimeout("se agotó")], solicitudes)
    with pytest.raises(ErrorConexion):
        voz.sintetizar("Hola.", config_voz(), cliente, tmp_path)
    assert len(solicitudes) == 1


def test_crear_cliente_usa_el_tiempo_de_espera_y_verifica_la_clave():
    cliente = voz.crear_cliente(config_voz(TIEMPO_ESPERA_API="7"))
    assert cliente._client_wrapper.get_timeout() == 7
    with pytest.raises(ErrorConfiguracion):
        voz.crear_cliente(config_voz(ELEVENLABS_API_KEY=""))
