"""Pruebas de T-12: src/validacion.py (RF-02, RF-16; spec 5.1, 5.2 y sección 10).

Casos del spec: pregunta vacía, solo espacios, más de 500 caracteres;
monto vacío, texto, cero y negativo.
"""

import pytest

from src.errores import ErrorValidacion
from src.validacion import (
    MENSAJE_MONTO_INVALIDO,
    MENSAJE_PREGUNTA_LARGA,
    MENSAJE_PREGUNTA_VACIA,
    validar_monto,
    validar_pregunta,
)


# ---------- validar_pregunta ----------

def test_pregunta_valida_se_devuelve_sin_espacios_en_los_extremos():
    assert validar_pregunta("  ¿Cuánto cobra?  ") == "¿Cuánto cobra?"


@pytest.mark.parametrize("texto", ["", "   ", "\n\t  ", None])
def test_pregunta_vacia_o_solo_espacios(texto):
    with pytest.raises(ErrorValidacion) as info:
        validar_pregunta(texto)
    assert str(info.value) == MENSAJE_PREGUNTA_VACIA


def test_pregunta_de_500_caracteres_es_valida():
    assert len(validar_pregunta("a" * 500)) == 500


def test_pregunta_de_501_caracteres_es_muy_larga():
    with pytest.raises(ErrorValidacion) as info:
        validar_pregunta("a" * 501)
    assert str(info.value) == MENSAJE_PREGUNTA_LARGA


def test_los_espacios_de_los_extremos_no_cuentan_para_el_largo():
    assert len(validar_pregunta("   " + "a" * 500 + "   ")) == 500


# ---------- validar_monto: válidos ----------

@pytest.mark.parametrize(
    "valor, esperado",
    [
        (30000, 30000.0),
        (30000.0, 30000.0),
        (0.5, 0.5),
        ("30000", 30000.0),
        ("  30000  ", 30000.0),
        ("₡30.000", 30000.0),       # formato de Costa Rica: punto = miles
        ("30.000", 30000.0),
        ("1.250.000", 1250000.0),
        ("₡ 15.000", 15000.0),
        ("30.000,50", 30000.5),
        ("1500,50", 1500.5),
        ("1500.5", 1500.5),
    ],
)
def test_monto_valido(valor, esperado):
    assert validar_monto(valor) == esperado


# ---------- validar_monto: inválidos ----------

@pytest.mark.parametrize(
    "valor",
    [
        None, "", "   ",                     # vacío
        "abc", "treinta mil", "30k", "₡",    # texto
        0, 0.0, "0", "0,00",                 # cero
        -5000, "-5000", "-₡5.000",           # negativo
        float("nan"), float("inf"), "inf",   # no son montos reales
        True, [30000],                       # otros tipos
    ],
)
def test_monto_invalido(valor):
    with pytest.raises(ErrorValidacion) as info:
        validar_monto(valor)
    assert str(info.value) == MENSAJE_MONTO_INVALIDO
