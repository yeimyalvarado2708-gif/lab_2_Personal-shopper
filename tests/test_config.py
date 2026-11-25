"""Pruebas de T-09: src/errores.py y src/config.py (RF-18, RNF-01, RNF-11).

Usan claves inventadas: nunca claves reales.
"""

import logging

import pytest

from src.config import cargar_config, informe_config, registrar_faltantes
from src.errores import (
    MENSAJE_NO_DISPONIBLE,
    MENSAJE_SOLO_TEXTO,
    ErrorAsistente,
    ErrorConexion,
    ErrorConfiguracion,
    ErrorCuota,
    ErrorServicio,
    ErrorValidacion,
)

CLAVE_GEMINI_FALSA = "AIzaFALSA_PRUEBA_0000000000000000000000"
CLAVE_ELEVEN_FALSA = "sk_FALSA_PRUEBA_000000000000000000000000000000000"

ENTORNO_COMPLETO = {
    "GEMINI_API_KEY": CLAVE_GEMINI_FALSA,
    "ELEVENLABS_API_KEY": CLAVE_ELEVEN_FALSA,
    "ELEVENLABS_VOICE_ID": "VOZ_DE_PRUEBA",
}


# ---------- errores.py ----------

def test_str_del_error_es_el_mensaje_para_el_usuario():
    error = ErrorConfiguracion(MENSAJE_NO_DISPONIBLE, "Falta GEMINI_API_KEY en .env")
    assert str(error) == MENSAJE_NO_DISPONIBLE
    assert "GEMINI_API_KEY" not in str(error)
    assert error.detalle_tecnico == "Falta GEMINI_API_KEY en .env"


def test_mensaje_de_validacion_personalizado():
    error = ErrorValidacion("Escriba una pregunta antes de enviar.")
    assert str(error) == "Escriba una pregunta antes de enviar."


@pytest.mark.parametrize(
    "clase", [ErrorConfiguracion, ErrorConexion, ErrorCuota, ErrorServicio, ErrorValidacion]
)
def test_todas_heredan_de_error_asistente_y_tienen_mensaje(clase):
    error = clase()
    assert isinstance(error, ErrorAsistente)
    assert error.mensaje_usuario
    for palabra in (".env", "API_KEY", "Traceback"):
        assert palabra not in error.mensaje_usuario


# ---------- config.py: valores ----------

def test_valores_por_defecto():
    cfg = cargar_config({})
    assert cfg.gemini_model == "gemini-3.5-flash-lite"
    assert cfg.elevenlabs_model == "eleven_multilingual_v2"
    assert cfg.limite_caracteres_respuesta == 400
    assert cfg.tiempo_espera_api == 20
    assert cfg.modo_demo is False


def test_valores_desde_el_entorno():
    cfg = cargar_config({**ENTORNO_COMPLETO, "MODO_DEMO": "TRUE", "TIEMPO_ESPERA_API": "15"})
    assert cfg.gemini_api_key == CLAVE_GEMINI_FALSA
    assert cfg.modo_demo is True
    assert cfg.tiempo_espera_api == 15


def test_espacios_en_blanco_cuentan_como_vacio():
    cfg = cargar_config({"GEMINI_API_KEY": "   "})
    assert cfg.faltantes_gemini() == ["GEMINI_API_KEY"]


@pytest.mark.parametrize(
    "variable, valor",
    [("TIEMPO_ESPERA_API", "veinte"), ("TIEMPO_ESPERA_API", "0"),
     ("LIMITE_CARACTERES_RESPUESTA", "-5"), ("MODO_DEMO", "quizas")],
)
def test_valor_invalido_lanza_error_que_nombra_la_variable(variable, valor):
    with pytest.raises(ErrorConfiguracion) as info:
        cargar_config({variable: valor})
    assert variable in info.value.detalle_tecnico


# ---------- config.py: faltantes (evidencia de T-09) ----------

def test_falta_clave_de_gemini():
    cfg = cargar_config({})
    with pytest.raises(ErrorConfiguracion) as info:
        cfg.verificar_gemini()
    assert str(info.value) == MENSAJE_NO_DISPONIBLE
    assert info.value.detalle_tecnico == "Falta GEMINI_API_KEY en .env"


def test_falta_voz_de_elevenlabs():
    cfg = cargar_config({"ELEVENLABS_API_KEY": CLAVE_ELEVEN_FALSA})
    with pytest.raises(ErrorConfiguracion) as info:
        cfg.verificar_elevenlabs()
    assert str(info.value) == MENSAJE_SOLO_TEXTO
    assert info.value.detalle_tecnico == "Falta ELEVENLABS_VOICE_ID en .env"


def test_configuracion_completa_no_lanza_error():
    cfg = cargar_config(ENTORNO_COMPLETO)
    cfg.verificar_gemini()
    cfg.verificar_elevenlabs()


def test_consola_nombra_lo_que_falta(caplog):
    cfg = cargar_config({"GEMINI_API_KEY": CLAVE_GEMINI_FALSA})
    with caplog.at_level(logging.WARNING, logger="personal_shopper"):
        faltan = registrar_faltantes(cfg)
    assert faltan == ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]
    assert "Falta ELEVENLABS_API_KEY en .env" in caplog.text
    assert "GEMINI_API_KEY" not in caplog.text


def test_modo_demo_no_avisa_faltantes():
    cfg = cargar_config({"MODO_DEMO": "true"})
    assert registrar_faltantes(cfg) == []


# ---------- config.py: las claves nunca se muestran (RNF-01) ----------

def test_repr_no_muestra_las_claves():
    texto = repr(cargar_config(ENTORNO_COMPLETO))
    assert CLAVE_GEMINI_FALSA not in texto
    assert CLAVE_ELEVEN_FALSA not in texto


def test_informe_no_muestra_las_claves():
    texto = "\n".join(informe_config(cargar_config(ENTORNO_COMPLETO)))
    assert CLAVE_GEMINI_FALSA not in texto
    assert CLAVE_ELEVEN_FALSA not in texto
    assert "GEMINI_API_KEY: configurada" in texto
