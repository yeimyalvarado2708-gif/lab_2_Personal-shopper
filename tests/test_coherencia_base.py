"""Pruebas de T-11: coherencia de data/base_conocimiento.json (RNF-14, RF-27).

- Los porcentajes y montos escritos en las FAQ coinciden con ``tarifas``
  (spec, sección 10: FAQ-02, FAQ-03 y FAQ-07; además FAQ-06 y una revisión general).
- Ninguna respuesta pasa de 400 caracteres.

Trabajan sobre la base REAL: si alguien edita un monto en el JSON y se le olvida
actualizar ``tarifas`` (o al revés), estas pruebas fallan y dicen qué FAQ revisar.
"""

import re

import pytest

from src.base_conocimiento import buscar_pregunta, cargar_base
from src.demo import telefono_whatsapp
from src.errores import TELEFONO_WHATSAPP

LIMITE_RESPUESTA = 400  # RF-27, decisión D-04

BASE = cargar_base()
TARIFAS = BASE["tarifas"]
RANGOS = TARIFAS["rangos_servicio"]
ENTREGA = TARIFAS["entrega_domicilio_con_cargo"]
ZONAS_CON_CARGO = BASE["zonas_domicilio"]["con_cargo"]
ZONAS_SIN_CARGO = BASE["zonas_domicilio"]["sin_cargo"]

LIMITE_INFERIOR = RANGOS[1]["desde"]  # ₡15.000
LIMITE_SUPERIOR = RANGOS[1]["hasta"]  # ₡40.000


# ---------- utilidades ----------

def montos(texto: str) -> list[int]:
    """Montos en colones escritos en el texto: '₡36.500' → 36500."""
    return [int(m.replace(".", "")) for m in re.findall(r"₡\s?(\d{1,3}(?:\.\d{3})*)", texto)]


def porcentajes(texto: str) -> list[int]:
    """Porcentajes escritos en el texto: '15%' → 15."""
    return [int(p) for p in re.findall(r"(\d+)\s?%", texto)]


def porcentaje_segun_tarifas(monto: float) -> int:
    for rango in RANGOS:
        hasta = rango["hasta"] if rango["hasta"] is not None else float("inf")
        if rango["desde"] <= monto <= hasta:
            return rango["porcentaje"]
    raise AssertionError(f"Ningún rango de 'tarifas' cubre ₡{monto}")


def respuesta(id_faq: str) -> str:
    faq = buscar_pregunta(BASE, id_faq)
    assert faq is not None, f"No existe {id_faq} en la base"
    return faq["respuesta"]


def test_utilidades_leen_montos_y_porcentajes():
    assert montos("factura de ₡30.000 + 15% (₡4.500) = ₡34.500.") == [30000, 4500, 34500]
    assert porcentajes("20% si…; 15 % si…") == [20, 15]


# ---------- la sección tarifas es coherente consigo misma ----------

def test_rangos_de_tarifas_sin_huecos():
    assert RANGOS[0]["desde"] == 0
    assert RANGOS[0]["hasta"] < LIMITE_INFERIOR
    assert RANGOS[2]["desde"] > LIMITE_SUPERIOR
    assert RANGOS[-1]["hasta"] is None
    # Casos de borde de RF-14: ₡15.000 y ₡40.000 exactos pagan 15%.
    assert porcentaje_segun_tarifas(14999) == 20
    assert porcentaje_segun_tarifas(15000) == 15
    assert porcentaje_segun_tarifas(40000) == 15
    assert porcentaje_segun_tarifas(40001) == 10


# ---------- FAQ-02: porcentajes y límites de los rangos ----------

def test_faq02_porcentajes_coinciden_con_tarifas():
    texto = respuesta("FAQ-02")
    esperados = [r["porcentaje"] for r in RANGOS]
    assert porcentajes(texto) == esperados, (
        f"FAQ-02 dice {porcentajes(texto)} %, pero 'tarifas' tiene {esperados} %"
    )


def test_faq02_limites_coinciden_con_tarifas():
    texto = respuesta("FAQ-02")
    esperados = {LIMITE_INFERIOR, LIMITE_SUPERIOR}
    assert set(montos(texto)) == esperados, (
        f"FAQ-02 menciona {sorted(set(montos(texto)))}, pero los límites de 'tarifas' son {sorted(esperados)}"
    )


# ---------- FAQ-03: el ejemplo de cálculo da lo mismo que las tarifas ----------

def test_faq03_ejemplo_calculado_con_tarifas():
    texto = respuesta("FAQ-03")
    entrega, factura, cargo, subtotal, total = montos(texto)
    pct = porcentaje_segun_tarifas(factura)

    assert entrega == ENTREGA, f"FAQ-03 dice ₡{entrega} de entrega, pero 'tarifas' dice ₡{ENTREGA}"
    assert porcentajes(texto) == [pct], (
        f"FAQ-03 usa {porcentajes(texto)} % para ₡{factura}, pero según 'tarifas' es {pct} %"
    )
    assert cargo == round(factura * pct / 100), f"FAQ-03: el cargo de ₡{factura} al {pct}% no es ₡{cargo}"
    assert subtotal == factura + cargo, f"FAQ-03: ₡{factura} + ₡{cargo} no es ₡{subtotal}"
    assert total == subtotal + ENTREGA, f"FAQ-03: ₡{subtotal} + ₡{ENTREGA} no es ₡{total}"


# ---------- FAQ-03, FAQ-06 y FAQ-07: costo y zonas de la entrega ----------

@pytest.mark.parametrize("id_faq", ["FAQ-03", "FAQ-06", "FAQ-07"])
def test_zonas_con_cargo_coinciden(id_faq):
    texto = respuesta(id_faq)
    faltan = [zona for zona in ZONAS_CON_CARGO if zona not in texto]
    assert not faltan, f"{id_faq} no menciona las zonas con cargo {faltan}"


@pytest.mark.parametrize("id_faq", ["FAQ-06", "FAQ-07"])
def test_costo_de_entrega_coincide_con_tarifas(id_faq):
    texto = respuesta(id_faq)
    assert montos(texto) == [ENTREGA], (
        f"{id_faq} menciona {montos(texto)}, pero la entrega con cargo es ₡{ENTREGA}"
    )


def test_faq06_cantidad_de_barrios_sin_cargo():
    texto = respuesta("FAQ-06")
    cantidad = int(re.search(r"(\d+)\s+barrios", texto).group(1))
    assert cantidad == len(ZONAS_SIN_CARGO), (
        f"FAQ-06 dice {cantidad} barrios, pero 'zonas_domicilio.sin_cargo' tiene {len(ZONAS_SIN_CARGO)}"
    )


# ---------- revisión general: ninguna FAQ trae montos sueltos ----------

@pytest.mark.parametrize("faq", BASE["preguntas"], ids=lambda f: f["id"])
def test_ningun_porcentaje_fuera_de_tarifas(faq):
    validos = {r["porcentaje"] for r in RANGOS}
    raros = [p for p in porcentajes(faq["respuesta"]) if p not in validos]
    assert not raros, f"{faq['id']} menciona {raros} %, que no está en 'tarifas'"


@pytest.mark.parametrize(
    "faq", [f for f in BASE["preguntas"] if f["id"] != "FAQ-03"], ids=lambda f: f["id"]
)
def test_ningun_monto_fuera_de_tarifas(faq):
    # FAQ-03 tiene un ejemplo con montos calculados; se revisa en su propia prueba.
    validos = {LIMITE_INFERIOR, LIMITE_SUPERIOR, ENTREGA}
    raros = [m for m in montos(faq["respuesta"]) if m not in validos]
    assert not raros, f"{faq['id']} menciona ₡{raros}, que no coincide con 'tarifas'"


# ---------- RF-27: máximo 400 caracteres ----------

@pytest.mark.parametrize("faq", BASE["preguntas"], ids=lambda f: f["id"])
def test_respuesta_maximo_400_caracteres(faq):
    largo = len(faq["respuesta"])
    assert largo <= LIMITE_RESPUESTA, (
        f"{faq['id']} tiene {largo} caracteres; el máximo es {LIMITE_RESPUESTA}"
    )


def test_el_telefono_de_respaldo_coincide_con_el_de_la_base():
    """T-29: si la base no se puede leer se usa TELEFONO_WHATSAPP; debe ser el mismo número."""
    assert telefono_whatsapp(BASE) == TELEFONO_WHATSAPP
