"""Cálculos de negocio en Python, sin API (D-08, RNF-04).

T-13: ``calcular_cuenta()`` y ``formatear_colones()`` (RF-13 a RF-15; spec 5.3).
T-14 agregará ``proxima_fecha_compra()`` y ``hoy_costa_rica()``.

Las tarifas y zonas se leen siempre de la base de conocimiento: si cambian en
el JSON, el cálculo cambia sin tocar este código (RNF-08).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from src.errores import ErrorBaseConocimiento, ErrorValidacion
from src.validacion import validar_monto

ZONA_PUNTO_ENTREGA = "Punto de entrega en el centro de Guápiles"

# Decisión de Yeimy (2026-11-24): una zona que no está en la base no se calcula;
# se avisa que será valorada.
MENSAJE_ZONA_INVALIDA = (
    "Zona no registrada. Será valorada y pronto le enviaremos más detalles."
)

# RF-15: leyenda que acompaña siempre al estimado.
LEYENDA_ESTIMADO = (
    "Este es un estimado. El total exacto se lo envío el jueves desde PriceSmart, "
    "solo con los productos disponibles."
)


def _redondear_colon(valor: float | Decimal) -> int:
    """Redondea al colón más cercano; las mitades suben (₡0,5 → ₡1).

    ``round()`` de Python redondea las mitades al par (``round(2.5) == 2``),
    por eso se usa ``Decimal`` con ``ROUND_HALF_UP``.
    """
    return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def zonas_para_formulario(datos: dict) -> list[str]:
    """Opciones de la lista desplegable de RF-13: punto de entrega, sin cargo y con cargo."""
    zonas = datos["zonas_domicilio"]
    return [ZONA_PUNTO_ENTREGA, *zonas["sin_cargo"], *zonas["con_cargo"]]


def porcentaje_servicio(monto: float, tarifas: dict) -> int:
    """Porcentaje del cargo del servicio según el rango de ``tarifas`` (RF-14).

    El monto se lleva a céntimos antes de compararlo, porque los rangos del JSON
    están escritos con céntimos (``14999.99``, ``40000.01``). Así ningún monto
    cae entre dos rangos.
    """
    en_centimos = float(Decimal(str(monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    for rango in tarifas["rangos_servicio"]:
        hasta = rango["hasta"] if rango["hasta"] is not None else float("inf")
        if rango["desde"] <= en_centimos <= hasta:
            return rango["porcentaje"]
    raise ErrorBaseConocimiento(
        detalle_tecnico=f"Ningún rango de 'tarifas.rangos_servicio' cubre el monto {en_centimos}."
    )


def costo_entrega(zona: str, datos: dict) -> int:
    """Costo de entrega de la zona: ₡0 en el punto de entrega y en zonas sin cargo.

    Lanza ``ErrorValidacion`` si la zona no está en la base.
    """
    zona = (zona or "").strip()
    zonas = datos["zonas_domicilio"]
    if zona == ZONA_PUNTO_ENTREGA or zona in zonas["sin_cargo"]:
        return 0
    if zona in zonas["con_cargo"]:
        return datos["tarifas"]["entrega_domicilio_con_cargo"]
    raise ErrorValidacion(MENSAJE_ZONA_INVALIDA)


def calcular_cuenta(monto: float, zona: str, primera_compra: bool, datos: dict) -> dict:
    """Estimado de la cuenta según RF-14 (spec 5.3).

    ``datos`` es la base de conocimiento (se usan ``tarifas`` y ``zonas_domicilio``).

    - Cargo del servicio: el porcentaje del rango sobre el monto.
    - Entrega: ₡2.000 solo si la zona está en ``zonas_domicilio.con_cargo``.
    - Primera compra: cortesía, el cargo del servicio y la entrega son ₡0.
    - El total se redondea al colón más cercano.

    ``porcentaje_servicio`` siempre informa el porcentaje del rango, aunque haya
    cortesía; ``cortesia_aplicada`` indica que no se cobró.

    Lanza ``ErrorValidacion`` si el monto no es válido o la zona no existe.
    """
    monto = validar_monto(monto)
    tarifas = datos["tarifas"]

    porcentaje = porcentaje_servicio(monto, tarifas)
    entrega = costo_entrega(zona, datos)  # valida la zona aunque haya cortesía

    if primera_compra:
        cargo, entrega = 0, 0
    else:
        cargo = _redondear_colon(Decimal(str(monto)) * porcentaje / 100)

    total = _redondear_colon(Decimal(str(monto)) + cargo + entrega)

    return {
        "monto_productos": monto,
        "porcentaje_servicio": porcentaje,
        "cargo_servicio": cargo,
        "cortesia_aplicada": bool(primera_compra),
        "costo_entrega": entrega,
        "total_estimado": total,
        "es_estimado": True,
    }


def formatear_colones(monto: float) -> str:
    """Formato de Costa Rica: 36500 → "₡36.500"; 30000.5 → "₡30.000,50".

    Usa punto para los miles y coma para los decimales. Los montos enteros
    se muestran sin decimales.
    """
    valor = Decimal(str(monto)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    signo = "-" if valor < 0 else ""
    valor = abs(valor)
    entero = int(valor)
    texto = f"{entero:,}".replace(",", ".")
    centimos = int((valor - entero) * 100)
    if centimos:
        texto += f",{centimos:02d}"
    return f"{signo}₡{texto}"
