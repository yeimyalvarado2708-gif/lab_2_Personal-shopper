"""Cálculos de negocio en Python, sin API (D-08, RNF-04).

T-13: ``calcular_cuenta()`` y ``formatear_colones()`` (RF-13 a RF-15; spec 5.3).
T-14: ``proxima_fecha_compra()`` y ``hoy_costa_rica()`` (RF-12, RF-28, RF-29; spec 5.4).

Las tarifas, zonas y el calendario se leen siempre de la base de conocimiento:
si cambian en el JSON, el cálculo cambia sin tocar este código (RNF-08).
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from src.errores import ErrorBaseConocimiento, ErrorValidacion
from src.validacion import validar_monto

ZONA_HORARIA_CR = ZoneInfo("America/Costa_Rica")  # RF-28
SEMANAS_MAXIMAS = 8  # RF-29

# RF-29: texto fijo cuando no hay fecha de compra en las próximas 8 semanas.
MENSAJE_SIN_FECHA = (
    "La próxima fecha de compra aún no está definida. "
    "Escríbanos por WhatsApp al 8888-0000."
)

_DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}

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


# ---------- fechas (T-14) ----------

def hoy_costa_rica(ahora: datetime | None = None) -> date:
    """Fecha de "hoy" en Costa Rica, sin importar la zona horaria del equipo (RF-28).

    ``ahora`` permite probar la función con un instante fijo; debe traer zona
    horaria (por ejemplo, UTC). Sin ``ahora`` se usa la hora actual.
    """
    if ahora is None:
        return datetime.now(ZONA_HORARIA_CR).date()
    if ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError("'ahora' debe incluir zona horaria (por ejemplo, UTC).")
    return ahora.astimezone(ZONA_HORARIA_CR).date()


def _numero_de_dia(nombre: str, campo: str) -> int:
    """'miércoles' → 2. Acepta mayúsculas y con o sin tilde."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", str(nombre).strip().lower())
        if unicodedata.category(c) != "Mn"
    )
    if sin_tildes not in _DIAS_SEMANA:
        raise ErrorBaseConocimiento(
            detalle_tecnico=f"'calendario_compras.{campo}' tiene un día no válido: {nombre!r}."
        )
    return _DIAS_SEMANA[sin_tildes]


def proxima_fecha_compra(hoy: date, calendario: dict) -> dict:
    """Próxima fecha de compra y fecha límite para enviar la lista (RF-12, RF-29; spec 5.4).

    - De lunes a miércoles: el jueves de esa semana. De jueves a domingo: el
      jueves de la semana siguiente (D-07). Es decir, el próximo día de compra
      DESPUÉS de hoy.
    - Si esa fecha está en ``fechas_canceladas``, pasa al siguiente, revisando
      como máximo 8 semanas.
    - La fecha límite es el día de ``dia_limite_lista`` anterior a la compra
      (el miércoles anterior al jueves).

    Devuelve las fechas en formato ``AAAA-MM-DD``. Si las 8 semanas están
    canceladas, ambas son ``None`` y se debe mostrar ``MENSAJE_SIN_FECHA``.
    """
    dia_compra = _numero_de_dia(calendario.get("dia_compra", "jueves"), "dia_compra")
    dia_limite = _numero_de_dia(
        calendario.get("dia_limite_lista", "miércoles"), "dia_limite_lista"
    )
    canceladas = set(calendario.get("fechas_canceladas", []))

    dias_hasta_compra = (dia_compra - hoy.weekday()) % 7 or 7  # siempre después de hoy
    primera_opcion = hoy + timedelta(days=dias_hasta_compra)

    for semana in range(SEMANAS_MAXIMAS):
        compra = primera_opcion + timedelta(weeks=semana)
        if compra.isoformat() not in canceladas:
            dias_antes = (compra.weekday() - dia_limite) % 7 or 7
            limite = compra - timedelta(days=dias_antes)
            return {
                "proxima_compra": compra.isoformat(),
                "fecha_limite_lista": limite.isoformat(),
            }

    return {"proxima_compra": None, "fecha_limite_lista": None}
