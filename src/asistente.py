"""Orquesta el chat y aplica los controles anti-invención (T-19).

Requisitos: RF-06, RF-07, RF-10, RF-21, RF-24, RF-25 (spec 4.2, pasos 2 a 7).

``responder()`` une el flujo del chat:

1. Valida la pregunta (RF-02).
2. Calcula la próxima compra con la fecha de hoy en Costa Rica (RF-12, RF-28).
3. Con ``MODO_DEMO=true`` usa ``demo.responder()``; si no, Gemini.
4. Aplica los controles, en este orden (spec 4.2, paso 6):
   a. RF-07: descarta las fuentes que no existen en la base.
   b. RF-21: sin información suficiente (o "suficiente" sin fuentes válidas)
      → mensaje fijo con WhatsApp. El texto de Gemini se descarta.
   c. RF-24: un monto en colones o un porcentaje que no existe en la base
      → mensaje fijo de la calculadora (con porcentajes y entrega de ``tarifas``).
   d. RF-25: ``aclaracion_pendiente`` → se agrega el texto fijo de WhatsApp.
   e. RF-10: la respuesta completa tiene máximo 400 caracteres.

5. Genera el audio con ``voz.sintetizar()`` (T-23). Si falla, el texto se
   entrega igual con un aviso (RF-19). En modo demo no se genera audio y se
   entrega el aviso de demo (RF-20). Sin información suficiente (RF-21) no se
   genera audio: la interfaz muestra el botón de WhatsApp (D-15; decisión de
   Yeimy en T-26, ahorra créditos).

Decisiones de Yeimy (2026-11-25, T-19):

- RF-24 más estricto: si el cliente escribió un monto en su pregunta (es un
  pedido de cálculo), la respuesta solo puede mencionar los montos fijos de
  ``tarifas`` (₡2.000, ₡15.000, ₡40.000). Así no pasa el ejemplo de FAQ-03
  (₡36.500) cuando el cliente pregunta justo por ₡30.000 en La Trocha.
- RF-24 también revisa porcentajes: solo se permiten los de la base.
- RF-10: si no termina ninguna oración dentro del límite, se corta en la
  última palabra completa y se agrega "…".
"""

from __future__ import annotations

import logging
import re
from datetime import date

from src import demo, gemini_client, voz
from src.calculadora import formatear_colones, hoy_costa_rica, proxima_fecha_compra
from src.config import Config, cargar_config
from src.errores import MENSAJE_AUDIO_DEMO, MENSAJE_AUDIO_NO_DISPONIBLE, ErrorAsistente
from src.texto import recortar
from src.validacion import validar_pregunta

logger = logging.getLogger("personal_shopper")

# RF-24: plantilla del texto fijo cuando la respuesta trae un monto o un
# porcentaje que no está en la base. Los porcentajes y el costo de entrega se
# toman de ``tarifas`` (decisión de Yeimy): ver ``mensaje_calculadora()``.
PLANTILLA_CALCULADORA = (
    "El total es su factura más un cargo de servicio del {minimo}% al {maximo}% "
    "según el monto, y {entrega} si la entrega es en una zona con cargo. "
    "Para calcular su cuenta, use la calculadora de estimado en esta misma página."
)

# Montos en colones: "₡2.000", "₡2000", "₡30.000,50", "2.000 colones".
# Separador de miles: punto o espacio fino (no el espacio común, para no unir
# "₡2.000 100" en un solo número).
_NUMERO = r"\d{1,3}(?:[.  ]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?"
_MONTO_CON_SIMBOLO = re.compile(rf"₡\s*({_NUMERO})")
_MONTO_CON_PALABRA = re.compile(rf"({_NUMERO})\s*colones\b", re.IGNORECASE)
_MONTO_EN_MILES = re.compile(r"\b\d+\s*mil\b", re.IGNORECASE)  # "30 mil"
_PORCENTAJE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:%|por\s*ciento\b)", re.IGNORECASE)

# RF-10: fin de oración = . ! ? o … seguido de espacio o del final del texto.


# ---------- números en el texto (RF-24) ----------

def _a_numero(texto: str) -> float:
    """"2.000" / "2000" / "30.000,50" → 2000.0 / 2000.0 / 30000.5."""
    entero, _, decimales = texto.partition(",")
    entero = re.sub(r"[.  ]", "", entero)
    return float(f"{entero}.{decimales}" if decimales else entero)


def extraer_montos(texto: str) -> set[float]:
    """Todos los montos en colones del texto, ya convertidos a número."""
    encontrados = _MONTO_CON_SIMBOLO.findall(texto) + _MONTO_CON_PALABRA.findall(texto)
    return {_a_numero(numero) for numero in encontrados}


def extraer_porcentajes(texto: str) -> set[float]:
    """Todos los porcentajes del texto: "15%", "15 %", "15 por ciento" → 15.0."""
    return {float(numero.replace(",", ".")) for numero in _PORCENTAJE.findall(texto)}


def pregunta_pide_calculo(pregunta: str) -> bool:
    """La pregunta trae un monto ("₡22.000", "22000 colones", "30 mil")."""
    return bool(extraer_montos(pregunta) or _MONTO_EN_MILES.search(pregunta))


def montos_de_tarifas(base: dict) -> set[float]:
    """Montos fijos de ``tarifas``: límites de los rangos y costo de entrega."""
    tarifas = base["tarifas"]
    montos = {float(tarifas["entrega_domicilio_con_cargo"])}
    for rango in tarifas["rangos_servicio"]:
        for limite in (rango.get("desde"), rango.get("hasta")):
            if limite:  # se omiten 0 y null
                montos.add(float(limite))
    return montos


def montos_de_la_base(base: dict) -> set[float]:
    """Montos de ``tarifas`` más todos los que aparecen en las respuestas de las FAQ."""
    montos = montos_de_tarifas(base)
    for faq in base["preguntas"]:
        montos |= extraer_montos(faq["respuesta"])
    return montos


def porcentajes_de_la_base(base: dict) -> set[float]:
    porcentajes = {float(r["porcentaje"]) for r in base["tarifas"]["rangos_servicio"]}
    for faq in base["preguntas"]:
        porcentajes |= extraer_porcentajes(faq["respuesta"])
    return porcentajes


def numeros_no_permitidos(respuesta: str, base: dict, pregunta: str) -> list[str]:
    """Montos y porcentajes de la respuesta que no están permitidos (RF-24).

    Devuelve una descripción de cada uno (para la consola); lista vacía si todo
    está bien.
    """
    if pregunta_pide_calculo(pregunta):
        montos_permitidos = montos_de_tarifas(base)  # decisión de Yeimy: más estricto
    else:
        montos_permitidos = montos_de_la_base(base)
    problemas = [
        f"monto ₡{monto:,.2f} no permitido"
        for monto in sorted(extraer_montos(respuesta) - montos_permitidos)
    ]
    problemas += [
        f"porcentaje {porcentaje:g}% no está en la base"
        for porcentaje in sorted(extraer_porcentajes(respuesta) - porcentajes_de_la_base(base))
    ]
    return problemas


# ---------- recorte (RF-10) ----------

# ---------- controles (RF-07, RF-21, RF-24, RF-25, RF-10) ----------

def _porcentaje_en_texto(valor: float) -> str:
    """20 → "20"; 12.5 → "12,5" (coma decimal de Costa Rica)."""
    return f"{valor:g}".replace(".", ",")


def mensaje_calculadora(base: dict) -> str:
    """Texto fijo de RF-24, armado con ``tarifas`` de la base.

    El menor y el mayor porcentaje salen de ``rangos_servicio`` y el costo de
    entrega de ``entrega_domicilio_con_cargo``: si cambian las tarifas, el
    mensaje cambia sin tocar el código.
    """
    tarifas = base["tarifas"]
    porcentajes = [float(r["porcentaje"]) for r in tarifas["rangos_servicio"]]
    return PLANTILLA_CALCULADORA.format(
        minimo=_porcentaje_en_texto(min(porcentajes)),
        maximo=_porcentaje_en_texto(max(porcentajes)),
        entrega=formatear_colones(tarifas["entrega_domicilio_con_cargo"]),
    )


def texto_aclaracion(base: dict) -> str:
    """Texto fijo de RF-25, con el número de ``negocio.contacto_humano``."""
    return f"Para lo demás, escríbanos por WhatsApp al {demo.telefono_whatsapp(base)}."


def _sin_informacion(base: dict, controles: list[str]) -> dict:
    return {
        "respuesta": demo.mensaje_sin_informacion(base),
        "fuentes": [],
        "categoria": demo.CATEGORIA_SIN_INFORMACION,
        "informacion_suficiente": False,
        "aclaracion_pendiente": False,
        "recortado": False,
        "controles": controles,
    }


def aplicar_controles(
    resultado: dict,
    base: dict,
    pregunta: str,
    limite: int,
    prefijo: str = "",
) -> dict:
    """Aplica los controles anti-invención a la respuesta de Gemini o del modo demo.

    ``resultado`` tiene el formato de spec 5.5. ``prefijo`` es
    "[RESPUESTA SIMULADA]" en modo demo: se quita antes de revisar y se vuelve
    a poner al final, contando dentro del límite.

    Devuelve el formato de spec 5.5 más dos campos: ``recortado`` (RF-10) y
    ``controles`` (qué control actuó y por qué, para la consola y la
    evaluación; nunca incluye la pregunta del cliente).
    """
    controles: list[str] = []
    respuesta = resultado["respuesta"].strip()
    if prefijo and respuesta.startswith(prefijo):
        respuesta = respuesta[len(prefijo):].strip()
    limite_texto = limite - (len(prefijo) + 1 if prefijo else 0)

    # a. RF-07: solo fuentes que existen en la base (o CALENDARIO).
    ids_validos = {faq["id"] for faq in base["preguntas"]} | {demo.FUENTE_CALENDARIO}
    fuentes: list[str] = []
    for fuente in resultado["fuentes"]:
        if fuente not in ids_validos:
            controles.append(f"RF-07: fuente {fuente} descartada (no existe en la base)")
        elif fuente not in fuentes:
            fuentes.append(fuente)

    # b. RF-21 (y RF-07): sin información → solo el mensaje fijo.
    if not resultado["informacion_suficiente"]:
        controles.append("RF-21: información insuficiente; se usa el mensaje fijo")
        final = _sin_informacion(base, controles)
    elif not fuentes:
        controles.append("RF-07: 'suficiente' sin fuentes válidas; se usa el mensaje fijo")
        final = _sin_informacion(base, controles)
    elif not respuesta:
        controles.append("RF-21: respuesta vacía; se usa el mensaje fijo")
        final = _sin_informacion(base, controles)
    else:
        final = {
            "respuesta": respuesta,
            "fuentes": fuentes,
            "categoria": resultado["categoria"],
            "informacion_suficiente": True,
            "aclaracion_pendiente": bool(resultado["aclaracion_pendiente"]),
            "recortado": False,
            "controles": controles,
        }

        # c. RF-24: montos y porcentajes que no existen en la base.
        problemas = numeros_no_permitidos(respuesta, base, pregunta)
        if problemas:
            controles.append(f"RF-24: {'; '.join(problemas)}; se usa el mensaje de la calculadora")
            final["respuesta"] = mensaje_calculadora(base)
            final["aclaracion_pendiente"] = False

        # d. RF-25 y e. RF-10: el texto fijo se agrega completo y el recorte
        # se hace en la parte de Gemini, para que el total no pase del límite.
        if final["aclaracion_pendiente"]:
            aclaracion = texto_aclaracion(base)
            cuerpo, recortado = recortar(final["respuesta"], limite_texto - len(aclaracion) - 1)
            final["respuesta"] = f"{cuerpo} {aclaracion}"
            controles.append("RF-25: se agregó el texto fijo de WhatsApp")
        else:
            final["respuesta"], recortado = recortar(final["respuesta"], limite_texto)
        if recortado:
            final["recortado"] = True
            controles.append(f"RF-10: respuesta recortada a {limite} caracteres")

    if prefijo:
        final["respuesta"] = f"{prefijo} {final['respuesta']}"
    if controles:
        logger.info("Controles aplicados: %s", " | ".join(controles))  # sin la pregunta (RNF-15)
    return final


# ---------- flujo del chat (spec 4.2) ----------

def responder(
    pregunta: str,
    base: dict,
    config: Config | None = None,
    hoy: date | None = None,
    cliente=None,
    cliente_voz=None,
    carpeta_cache=None,
) -> dict:
    """Responde una pregunta del chat, ya con los controles aplicados.

    - ``config``: si no se pasa, se lee del ``.env``.
    - ``hoy``: si no se pasa, se usa la fecha de hoy en Costa Rica (RF-28).
    - ``cliente``: un cliente de Gemini reutilizable (ver ``gemini_client``).
    - ``cliente_voz`` y ``carpeta_cache``: para ``voz.sintetizar()`` (las
      pruebas pasan un cliente falso y una carpeta temporal).

    Lanza ``ErrorValidacion`` si la pregunta no es válida, y los errores de
    ``gemini_client`` si Gemini falla (spec, sección 7).

    Devuelve el formato de spec 5.5 más ``recortado``, ``controles``,
    ``modo_demo`` y el audio: ``audio`` (bytes MP3 o ``None``),
    ``audio_desde_cache`` y ``aviso_audio`` (texto para el cliente cuando no
    hay audio, o ``None``). Un error de audio nunca impide entregar el texto.
    """
    pregunta = validar_pregunta(pregunta)
    config = config or cargar_config()
    fechas = proxima_fecha_compra(hoy or hoy_costa_rica(), base["calendario_compras"])

    if config.modo_demo:
        crudo = demo.responder(pregunta, base, fechas)
        prefijo = demo.PREFIJO_SIMULADA
    else:
        crudo = gemini_client.generar_respuesta(pregunta, base, fechas, config, cliente)
        prefijo = ""

    resultado = aplicar_controles(
        crudo, base, pregunta, config.limite_caracteres_respuesta, prefijo
    )
    resultado["modo_demo"] = config.modo_demo
    if resultado["informacion_suficiente"]:
        resultado.update(_audio_de(resultado["respuesta"], config, cliente_voz, carpeta_cache))
    else:  # D-15: en lugar del audio, botón de WhatsApp (sin aviso ni gasto de créditos)
        resultado.update({"audio": None, "audio_desde_cache": False, "aviso_audio": None})
    return resultado


def _audio_de(texto: str, config: Config, cliente_voz, carpeta_cache) -> dict:
    """Audio de la respuesta, o el aviso si no se puede generar (RF-19, RF-20)."""
    sin_audio = {"audio": None, "audio_desde_cache": False}
    if config.modo_demo:
        return {**sin_audio, "aviso_audio": MENSAJE_AUDIO_DEMO}
    try:
        audio = voz.sintetizar(texto, config, cliente_voz, carpeta_cache)
    except ErrorAsistente as error:
        logger.warning("Audio no disponible: %s", error.detalle_tecnico or type(error).__name__)
        return {**sin_audio, "aviso_audio": str(error)}
    except Exception as error:  # RF-19: un fallo inesperado del audio no borra el texto
        logger.warning("Audio no disponible por un error inesperado: %s", type(error).__name__)
        return {**sin_audio, "aviso_audio": MENSAJE_AUDIO_NO_DISPONIBLE}
    return {"audio": audio["audio"], "audio_desde_cache": audio["desde_cache"], "aviso_audio": None}
