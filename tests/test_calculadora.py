"""Pruebas de la calculadora (spec 5.3 y sección 10).

T-13: parte de la cuenta: los 7 casos de referencia, bordes, cortesía, zonas
y ``formatear_colones()``. T-14 agregará los casos de fechas y zona horaria.
"""

import copy

import pytest

from src.base_conocimiento import cargar_base
from src.calculadora import (
    LEYENDA_ESTIMADO,
    ZONA_PUNTO_ENTREGA,
    calcular_cuenta,
    formatear_colones,
    porcentaje_servicio,
    zonas_para_formulario,
)
from src.errores import ErrorValidacion

BASE = cargar_base()
SIN_CARGO = BASE["zonas_domicilio"]["sin_cargo"][0]  # "Cuadrante"


# ---------- los 7 casos de referencia (spec 5.3, HU-02) ----------

@pytest.mark.parametrize(
    "monto, zona, primera, total",
    [
        (10000, SIN_CARGO, False, 12000),
        (15000, SIN_CARGO, False, 17250),      # borde: 15%
        (30000, "La Trocha", False, 36500),
        (40000, SIN_CARGO, False, 46000),      # borde: 15%
        (50000, SIN_CARGO, False, 55000),
        (30000, SIN_CARGO, True, 30000),
        (30000, "Buenos Aires", True, 30000),  # la cortesía cubre servicio y entrega
    ],
    ids=["10000", "15000-borde", "30000-LaTrocha", "40000-borde", "50000",
         "30000-primera", "30000-BuenosAires-primera"],
)
def test_casos_de_referencia(monto, zona, primera, total):
    assert calcular_cuenta(monto, zona, primera, BASE)["total_estimado"] == total


def test_salida_completa_coincide_con_el_spec():
    assert calcular_cuenta(30000, "La Trocha", False, BASE) == {
        "monto_productos": 30000,
        "porcentaje_servicio": 15,
        "cargo_servicio": 4500,
        "cortesia_aplicada": False,
        "costo_entrega": 2000,
        "total_estimado": 36500,
        "es_estimado": True,
    }


def test_cortesia_pone_en_cero_servicio_y_entrega():
    r = calcular_cuenta(30000, "Buenos Aires", True, BASE)
    assert r["cortesia_aplicada"] is True
    assert r["cargo_servicio"] == 0
    assert r["costo_entrega"] == 0
    assert r["porcentaje_servicio"] == 15  # se informa el rango aunque no se cobre


# ---------- rangos y bordes ----------

@pytest.mark.parametrize(
    "monto, porcentaje",
    [(0.01, 20), (14999.99, 20), (14999.994, 20), (14999.995, 15), (15000, 15),
     (40000, 15), (40000.004, 15), (40000.01, 10), (1_000_000, 10)],
)
def test_porcentaje_por_rango_sin_huecos(monto, porcentaje):
    assert porcentaje_servicio(monto, BASE["tarifas"]) == porcentaje


def test_redondeo_al_colon_mas_cercano_las_mitades_suben():
    # 10002,50 × 20% = 2000,50 → ₡2.001 (round() de Python daría 2000)
    r = calcular_cuenta(10002.5, SIN_CARGO, False, BASE)
    assert r["cargo_servicio"] == 2001
    assert r["total_estimado"] == 12004  # 10002,50 + 2001 = 12003,50 → 12004


# ---------- zonas ----------

def test_punto_de_entrega_no_cobra_entrega():
    assert calcular_cuenta(30000, ZONA_PUNTO_ENTREGA, False, BASE)["costo_entrega"] == 0


@pytest.mark.parametrize("zona", BASE["zonas_domicilio"]["sin_cargo"])
def test_zonas_sin_cargo(zona):
    assert calcular_cuenta(30000, zona, False, BASE)["costo_entrega"] == 0


@pytest.mark.parametrize("zona", BASE["zonas_domicilio"]["con_cargo"])
def test_zonas_con_cargo(zona):
    assert calcular_cuenta(30000, zona, False, BASE)["costo_entrega"] == 2000


@pytest.mark.parametrize("zona", ["Limón", "", "la trocha", None])
def test_zona_que_no_existe(zona):
    with pytest.raises(ErrorValidacion) as info:
        calcular_cuenta(30000, zona, False, BASE)
    assert str(info.value) == (
        "Zona no registrada. Será valorada y pronto le enviaremos más detalles."
    )


def test_zona_invalida_se_rechaza_aunque_sea_primera_compra():
    with pytest.raises(ErrorValidacion):
        calcular_cuenta(30000, "Limón", True, BASE)


def test_lista_del_formulario():
    zonas = zonas_para_formulario(BASE)
    assert zonas[0] == ZONA_PUNTO_ENTREGA
    assert len(zonas) == 1 + 23 + 4
    assert "La Trocha" in zonas and "Barrio Pinares" in zonas


# ---------- monto inválido (RF-16) ----------

@pytest.mark.parametrize("monto", [0, -5000, None, "abc"])
def test_monto_invalido_no_calcula(monto):
    with pytest.raises(ErrorValidacion):
        calcular_cuenta(monto, SIN_CARGO, False, BASE)


# ---------- las tarifas salen del JSON (RNF-08) ----------

def test_si_cambian_las_tarifas_cambia_el_calculo():
    datos = copy.deepcopy(BASE)
    datos["tarifas"]["entrega_domicilio_con_cargo"] = 2500
    datos["tarifas"]["rangos_servicio"][1]["porcentaje"] = 12
    r = calcular_cuenta(30000, "La Trocha", False, datos)
    assert r["cargo_servicio"] == 3600
    assert r["total_estimado"] == 30000 + 3600 + 2500


# ---------- formatear_colones y leyenda ----------

@pytest.mark.parametrize(
    "monto, texto",
    [(36500, "₡36.500"), (2000, "₡2.000"), (500, "₡500"), (0, "₡0"),
     (1250000, "₡1.250.000"), (30000.0, "₡30.000"), (30000.5, "₡30.000,50"),
     (12003.456, "₡12.003,46"), (-500, "-₡500")],
)
def test_formatear_colones(monto, texto):
    assert formatear_colones(monto) == texto


def test_leyenda_de_estimado_rf15():
    assert LEYENDA_ESTIMADO == (
        "Este es un estimado. El total exacto se lo envío el jueves desde PriceSmart, "
        "solo con los productos disponibles."
    )
