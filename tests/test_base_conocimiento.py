"""Pruebas de T-10: src/base_conocimiento.py (RF-03; spec, secciones 8 y 10).

Casos del spec: carga correcta, JSON mal formado, campos faltantes e ID repetidos.
Además: archivo ausente, secciones obligatorias y fechas canceladas.
"""

import copy
import json

import pytest

from src.base_conocimiento import buscar_pregunta, cargar_base, validar_base
from src.errores import MENSAJE_NO_DISPONIBLE, ErrorBaseConocimiento


def base_minima() -> dict:
    """Una base pequeña y válida para modificar en cada prueba."""
    return {
        "preguntas": [
            {"id": "FAQ-01", "categoria": "Servicio", "pregunta": "¿Cómo funciona?",
             "respuesta": "Usted envía su lista."},
            {"id": "FAQ-02", "categoria": "Tarifas", "pregunta": "¿Cuánto cobra?",
             "respuesta": "Un porcentaje de la factura."},
        ],
        "tarifas": {"rangos_servicio": []},
        "zonas_domicilio": {"sin_cargo": [], "con_cargo": []},
        "calendario_compras": {"dia_compra": "jueves", "fechas_canceladas": []},
    }


def escribir(tmp_path, contenido: str):
    ruta = tmp_path / "base_conocimiento.json"
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def detalle_del_error(base) -> str:
    with pytest.raises(ErrorBaseConocimiento) as info:
        validar_base(base)
    assert str(info.value) == MENSAJE_NO_DISPONIBLE  # el cliente nunca ve el detalle
    return info.value.detalle_tecnico


# ---------- carga correcta ----------

def test_carga_la_base_real_del_proyecto():
    base = cargar_base()
    assert len(base["preguntas"]) == base["metadatos"]["total_preguntas"]
    for seccion in ("tarifas", "zonas_domicilio", "calendario_compras"):
        assert seccion in base


def test_carga_un_archivo_valido(tmp_path):
    ruta = escribir(tmp_path, json.dumps(base_minima(), ensure_ascii=False))
    assert cargar_base(ruta)["preguntas"][0]["id"] == "FAQ-01"


def test_buscar_pregunta():
    base = base_minima()
    assert buscar_pregunta(base, "FAQ-02")["categoria"] == "Tarifas"
    assert buscar_pregunta(base, "FAQ-99") is None


# ---------- archivo ausente o JSON mal formado ----------

def test_archivo_ausente(tmp_path):
    with pytest.raises(ErrorBaseConocimiento) as info:
        cargar_base(tmp_path / "no_existe.json")
    assert str(info.value) == MENSAJE_NO_DISPONIBLE
    assert "no_existe.json" in info.value.detalle_tecnico
    assert "no_existe.json" not in str(info.value)


def test_json_mal_formado(tmp_path):
    ruta = escribir(tmp_path, '{"preguntas": [ {"id": "FAQ-01",} ]')
    with pytest.raises(ErrorBaseConocimiento) as info:
        cargar_base(ruta)
    assert "no es un JSON válido" in info.value.detalle_tecnico
    assert "línea 1" in info.value.detalle_tecnico


def test_json_que_no_es_objeto():
    assert "objeto JSON" in detalle_del_error([1, 2, 3])


# ---------- lista de preguntas y campos faltantes ----------

@pytest.mark.parametrize("valor", [None, [], "texto"])
def test_sin_lista_de_preguntas(valor):
    base = base_minima()
    base["preguntas"] = valor
    assert "'preguntas'" in detalle_del_error(base)


@pytest.mark.parametrize("campo", ["id", "categoria", "pregunta", "respuesta"])
def test_campo_faltante(campo):
    base = base_minima()
    del base["preguntas"][1][campo]
    detalle = detalle_del_error(base)
    assert f"'{campo}'" in detalle


@pytest.mark.parametrize("valor", ["", "   ", None, 5])
def test_campo_vacio_o_de_otro_tipo(valor):
    base = base_minima()
    base["preguntas"][0]["respuesta"] = valor
    detalle = detalle_del_error(base)
    assert "FAQ-01" in detalle and "'respuesta'" in detalle


# ---------- ID repetidos ----------

def test_id_repetido():
    base = base_minima()
    base["preguntas"].append(copy.deepcopy(base["preguntas"][0]))
    assert "'FAQ-01' está repetido" in detalle_del_error(base)


# ---------- secciones obligatorias ----------

@pytest.mark.parametrize("seccion", ["tarifas", "zonas_domicilio", "calendario_compras"])
def test_falta_seccion_obligatoria(seccion):
    base = base_minima()
    del base[seccion]
    assert f"'{seccion}'" in detalle_del_error(base)


# ---------- fechas canceladas ----------

def test_fecha_cancelada_valida():
    base = base_minima()
    base["calendario_compras"]["fechas_canceladas"] = ["2026-12-24"]
    assert validar_base(base) is base


@pytest.mark.parametrize("fecha", ["24/12/2026", "20261224", "2026-12-1", 20261224])
def test_fecha_cancelada_con_formato_incorrecto(fecha):
    base = base_minima()
    base["calendario_compras"]["fechas_canceladas"] = [fecha]
    assert "AAAA-MM-DD" in detalle_del_error(base)


def test_fecha_cancelada_que_no_existe():
    base = base_minima()
    base["calendario_compras"]["fechas_canceladas"] = ["2026-02-30"]
    assert "no es una fecha real" in detalle_del_error(base)
