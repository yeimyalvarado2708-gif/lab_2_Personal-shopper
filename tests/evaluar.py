"""Evaluación del asistente con Gemini real (T-33; spec, secciones 10 y 11).

Recorre ``tests/preguntas_evaluacion.json`` **una sola vez**, solo con Gemini
(sin audio: no gasta créditos de ElevenLabs), y guarda:

- ``evidencias/evaluacion_AAAA-MM-DD.json``: todos los datos de cada caso.
- ``evidencias/evaluacion_AAAA-MM-DD.md``: reporte legible con una columna
  "Revisión de Yeimy" para la revisión humana (decisión de Yeimy).

Uso (desde la carpeta del proyecto, con el entorno activado):

    python tests/evaluar.py           # Gemini real: ~33 solicitudes, ~5 minutos
    python tests/evaluar.py --demo    # ensayo sin APIs ni archivos (modo demo)
    python tests/evaluar.py --casos EV-24   # reevaluar solo esos casos (R-05, ciclo C-06)

Con ``--casos`` se guarda aparte, en ``evidencias/reevaluacion_AAAA-MM-DD_EV-24.*``:
la evaluación original de T-33 no se toca. Los mínimos de la sección 11 se
miden sobre el conjunto completo, así que una reevaluación parcial no dice
"cumple" ni "no cumple" por grupo.

Cómo se evalúa cada caso (regla del propio conjunto, ``como_se_evalua``):
1. Las fuentes mostradas incluyen las ``fuentes_esperadas``.
2. ``informacion_suficiente`` y ``aclaracion_pendiente`` coinciden (``null`` = no se evalúa).
3. El texto contiene todo ``debe_contener`` y nada de ``no_debe_contener``,
   sin distinguir mayúsculas.
4. Una revisión humana confirma el criterio (reporte ``.md``).

Decisiones de Yeimy (2026-11-26, T-33):
- Se evalúa la respuesta **final**, la que ve el cliente (Gemini + controles
  RF-07, RF-21, RF-24, RF-25 y RF-10); también se guarda la de Gemini sin
  controles y qué control actuó.
- Un término que empieza con dígito no puede ir pegado a otro dígito antes:
  "5%" no coincide dentro de "15%" (EV-27), pero sí en "de 5%". El conjunto no
  cambia.
- Si Gemini responde "cuota agotada", se espera 60 s y se reintenta una vez.
  Entre preguntas se deja al menos ``INTERVALO_MINIMO`` segundos (límite
  gratuito: 15 por minuto).
- La revisión humana se hace en el reporte ``.md``.

El conjunto no se modifica después de ver los resultados (regla del conjunto).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import replace
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:  # para correrlo como "python tests/evaluar.py"
    sys.path.insert(0, str(RAIZ))

from src import demo, gemini_client  # noqa: E402
from src.asistente import aplicar_controles  # noqa: E402
from src.base_conocimiento import cargar_base  # noqa: E402
from src.calculadora import hoy_costa_rica, proxima_fecha_compra  # noqa: E402
from src.config import cargar_config  # noqa: E402
from src.errores import ErrorAsistente, ErrorCuota  # noqa: E402
from src.validacion import validar_pregunta  # noqa: E402

CONJUNTO = RAIZ / "tests" / "preguntas_evaluacion.json"
CARPETA_EVIDENCIAS = RAIZ / "evidencias"
INTERVALO_MINIMO = 4.5  # segundos entre el inicio de dos preguntas (≤ 13,3 por minuto)
ESPERA_CUOTA = 60  # segundos antes de reintentar tras "cuota agotada"
TIPOS = ("dentro_base", "fuera_base", "manipulacion", "calculo_chat", "dos_partes")


# ---------- reglas de comparación ----------

def contiene(texto: str, termino: str) -> bool:
    """¿``texto`` contiene ``termino``? Sin distinguir mayúsculas.

    Si el término empieza con dígito, no puede ir pegado a otro dígito antes:
    "5%" no está en "15%" (decisión de Yeimy, T-33). El final no se restringe:
    "CR0" (EV-28) debe encontrarse dentro de una cuenta inventada "CR05…".
    """
    patron = re.escape(termino.lower())
    if termino[:1].isdigit():
        patron = r"(?<!\d)" + patron
    return re.search(patron, texto.lower()) is not None


def evaluar_caso(caso: dict, final: dict, limite: int = 400) -> dict:
    """Las comprobaciones automáticas (1 a 3) de un caso sobre la respuesta final."""
    esperado = caso["resultado_esperado"]
    texto = final["respuesta"]
    faltan_fuentes = [f for f in esperado["fuentes_esperadas"] if f not in final["fuentes"]]
    faltan_textos = [t for t in esperado["debe_contener"] if not contiene(texto, t)]
    prohibidos = [t for t in esperado["no_debe_contener"] if contiene(texto, t)]

    def coincide(campo: str) -> bool | None:
        if esperado[campo] is None:
            return None  # no se evalúa
        return bool(final[campo]) == esperado[campo]

    revision = {
        "fuentes": not faltan_fuentes,
        "informacion_suficiente": coincide("informacion_suficiente"),
        "aclaracion_pendiente": coincide("aclaracion_pendiente"),
        "debe_contener": not faltan_textos,
        "no_debe_contener": not prohibidos,
    }
    return {
        "comprobaciones": revision,
        "faltan_fuentes": faltan_fuentes,
        "faltan_textos": faltan_textos,
        "textos_prohibidos_encontrados": prohibidos,
        "largo": len(texto),
        "largo_ok": len(texto) <= limite,  # RF-10 (informativo)
        "pasa_automatico": all(v is not False for v in revision.values()),
    }


def umbrales(metadatos: dict) -> dict[str, int]:
    """"al menos 18 de 20 correctas" → 18; "5 de 5" → 5."""
    return {
        clave: int(re.search(r"(\d+)\s+de\s+\d+", texto).group(1))
        for clave, texto in metadatos["umbrales_aprobacion"].items()
    }


def resumen(resultados: list[dict], metadatos: dict, parcial: bool = False) -> dict:
    """Aprobados por tipo y por HU-01, contra los umbrales de la sección 11.

    Si ``parcial`` (reevaluación con ``--casos``), los mínimos no se aplican:
    ``minimo`` y ``cumple`` quedan en ``None``.
    """
    minimos = umbrales(metadatos)
    grupos = {tipo: [r for r in resultados if r["tipo"] == tipo] for tipo in TIPOS}
    grupos["hu01"] = [r for r in resultados if r["hu01"]]
    salida = {}
    for nombre, casos in grupos.items():
        aprobados = sum(1 for r in casos if r["evaluacion"] and r["evaluacion"]["pasa_automatico"])
        salida[nombre] = {
            "aprobados": aprobados,
            "total": len(casos),
            "minimo": None if parcial else minimos[nombre],
            "cumple": None if parcial else aprobados >= minimos[nombre],
        }
    salida["errores"] = [r["id"] for r in resultados if r["error"]]
    salida["respuestas_de_mas_de_400"] = [
        r["id"] for r in resultados if r["evaluacion"] and not r["evaluacion"]["largo_ok"]]
    return salida


# ---------- ejecución ----------

def responder_sin_audio(pregunta: str, base: dict, fechas: dict, config, cliente=None):
    """El flujo de ``asistente.responder()`` sin audio: (respuesta de Gemini, respuesta final)."""
    pregunta = validar_pregunta(pregunta)
    if config.modo_demo:
        crudo, prefijo = demo.responder(pregunta, base, fechas), demo.PREFIJO_SIMULADA
    else:
        crudo = gemini_client.generar_respuesta(pregunta, base, fechas, config, cliente)
        prefijo = ""
    final = aplicar_controles(crudo, base, pregunta, config.limite_caracteres_respuesta, prefijo)
    return crudo, final


def ejecutar(casos: list[dict], base: dict, config, hoy: date, cliente=None,
             dormir=time.sleep, reloj=time.monotonic, avisar=print) -> list[dict]:
    """Recorre los casos en orden, con pausas y un reintento si se agota la cuota."""
    fechas = proxima_fecha_compra(hoy, base["calendario_compras"])
    resultados = []
    ultimo_inicio = None
    for caso in casos:
        if ultimo_inicio is not None and not config.modo_demo:
            dormir(max(0.0, INTERVALO_MINIMO - (reloj() - ultimo_inicio)))
        crudo = final = error = None
        intentos = 0
        while True:
            intentos += 1
            ultimo_inicio = reloj()
            try:
                crudo, final = responder_sin_audio(caso["pregunta"], base, fechas, config, cliente)
                break
            except ErrorCuota as e:
                if intentos == 1:
                    avisar(f"   {caso['id']}: cuota agotada; espero {ESPERA_CUOTA} s y reintento…")
                    dormir(ESPERA_CUOTA)
                    continue
                error = f"ErrorCuota: {e.detalle_tecnico or e}"
                break
            except ErrorAsistente as e:
                error = f"{type(e).__name__}: {e.detalle_tecnico or e}"
                break
        evaluacion = evaluar_caso(caso, final, config.limite_caracteres_respuesta) if final else None
        resultados.append({
            "id": caso["id"], "tipo": caso["tipo"], "hu01": caso["hu01"],
            "pregunta": caso["pregunta"], "criterio": caso["criterio"],
            "resultado_esperado": caso["resultado_esperado"],
            "respuesta_gemini": crudo, "respuesta_final": final,
            "intentos": intentos, "error": error, "evaluacion": evaluacion,
            "revision_humana": None,  # se llena en el reporte .md
        })
        marca = "ERROR" if error else ("✅" if evaluacion["pasa_automatico"] else "❌")
        avisar(f"{caso['id']} {marca} {caso['tipo']}" + (f" — {error}" if error else ""))
    return resultados


# ---------- reportes ----------

def _celda(texto: object) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")


def _marca_minimo(g: dict) -> str:
    """Las dos últimas columnas del resumen: mínimo y si cumple ("—" si no aplica)."""
    if g["cumple"] is None:
        return "— | no aplica"
    return f"{g['minimo']} | {'✅' if g['cumple'] else '❌'}"


def reporte_md(datos: dict) -> str:
    """Reporte para la revisión humana (decisión de Yeimy)."""
    m, r = datos["metadatos"], datos["resumen"]
    parcial = bool(m.get("casos_evaluados"))
    titulo = (f"# Reevaluación de {', '.join(m['casos_evaluados'])} · {m['fecha']}" if parcial
              else f"# Evaluación del asistente · {m['fecha']}")
    lineas = [titulo, ""]
    if parcial:
        lineas += [f"Reevaluación parcial ({m['motivo']}). La evaluación original "
                   f"`{m['reevaluacion_de']}` no se modificó. Los mínimos de la sección 11 se miden "
                   "sobre el conjunto completo y no se aplican aquí.", ""]
    lineas += [
        f"Modelo `{m['modelo']}` · temperatura {m['temperatura']} · conjunto v{m['version_conjunto']} · "
        f"base v{m['version_base']} · respuesta evaluada: final, con controles · sin audio.",
        "",
        "## Resumen automático (comprobaciones 1 a 3)",
        "",
        "| Grupo | Aprobados | Mínimo (sección 11) | ¿Cumple? |",
        "|---|---|---|---|",
    ]
    for grupo in (*TIPOS, "hu01"):
        g = r[grupo]
        if g["total"] == 0:
            continue  # grupo sin casos en una reevaluación parcial
        lineas.append(f"| {grupo} | {g['aprobados']} de {g['total']} | {_marca_minimo(g)} |")
    lineas += ["", f"Errores: {', '.join(r['errores']) or 'ninguno'} · "
               f"Respuestas de más de 400 caracteres: {', '.join(r['respuestas_de_mas_de_400']) or 'ninguna'}",
               "", "## Revisión humana (comprobación 4)", "",
               "Marque cada caso con ✅ o ❌ en la última columna y agregue un comentario si hace falta.", "",
               "| ID | Tipo | Automático | Revisión de Yeimy |", "|---|---|---|---|"]
    for c in datos["casos"]:
        auto = "ERROR" if c["error"] else ("✅" if c["evaluacion"]["pasa_automatico"] else "❌")
        lineas.append(f"| {c['id']} | {c['tipo']}{' · HU-01' if c['hu01'] else ''} | {auto} | |")
    lineas += ["", "## Detalle de cada caso", ""]
    for c in datos["casos"]:
        lineas += [f"### {c['id']} · {c['tipo']}", "",
                   f"**Pregunta:** {_celda(c['pregunta'])}", "",
                   f"**Criterio:** {_celda(c['criterio'])}", ""]
        if c["error"]:
            lineas += [f"**Error:** {_celda(c['error'])}", ""]
            continue
        f, e = c["respuesta_final"], c["evaluacion"]
        lineas += [f"**Respuesta final:** {_celda(f['respuesta'])}", "",
                   f"Fuentes: {', '.join(f['fuentes']) or '—'} · Categoría: {f['categoria']} · "
                   f"información suficiente: {f['informacion_suficiente']} · aclaración: "
                   f"{f['aclaracion_pendiente']} · {e['largo']} caracteres", ""]
        if f["controles"]:
            lineas += [f"Controles que actuaron: {_celda('; '.join(f['controles']))}", ""]
        if c["respuesta_gemini"] and c["respuesta_gemini"]["respuesta"] != f["respuesta"]:
            lineas += [f"Respuesta de Gemini sin controles: {_celda(c['respuesta_gemini']['respuesta'])}", ""]
        detalles = []
        if e["faltan_fuentes"]:
            detalles.append(f"faltan fuentes {e['faltan_fuentes']}")
        if e["faltan_textos"]:
            detalles.append(f"faltan textos {e['faltan_textos']}")
        if e["textos_prohibidos_encontrados"]:
            detalles.append(f"textos prohibidos {e['textos_prohibidos_encontrados']}")
        for campo in ("informacion_suficiente", "aclaracion_pendiente"):
            if e["comprobaciones"][campo] is False:
                detalles.append(f"{campo} no coincide")
        lineas += [f"Automático: {'✅ pasa' if e['pasa_automatico'] else '❌ ' + '; '.join(detalles)}", "",
                   "Revisión de Yeimy: ", ""]
    return "\n".join(lineas) + "\n"


def rutas(fecha: str, carpeta: Path, casos: list[str] | None = None) -> tuple[Path, Path]:
    """Las rutas del .json y el .md de la evaluación de ``fecha`` (AAAA-MM-DD).

    Con ``casos`` (reevaluación): ``reevaluacion_AAAA-MM-DD_EV-24.*``.
    """
    nombre = f"reevaluacion_{fecha}_{'_'.join(casos)}" if casos else f"evaluacion_{fecha}"
    base = carpeta / nombre
    return base.with_suffix(".json"), base.with_suffix(".md")


def existentes(fecha: str, carpeta: Path, casos: list[str] | None = None) -> list[Path]:
    """Los archivos de esa evaluación (o reevaluación) que ya existen."""
    return [ruta for ruta in rutas(fecha, carpeta, casos) if ruta.exists()]


def evaluacion_original(carpeta: Path) -> str:
    """El nombre de la evaluación completa más reciente (``evaluacion_AAAA-MM-DD``), o "—"."""
    previas = sorted(carpeta.glob("evaluacion_*.json"))
    return previas[-1].stem if previas else "—"


def elegir_casos(todos: list[dict], ids: list[str] | None) -> list[dict]:
    """Los casos pedidos con ``--casos``, en el orden del conjunto; error si alguno no existe."""
    if not ids:
        return todos
    conocidos = {c["id"] for c in todos}
    desconocidos = [i for i in ids if i not in conocidos]
    if desconocidos:
        raise ValueError(f"Casos que no están en el conjunto: {', '.join(desconocidos)}")
    return [c for c in todos if c["id"] in ids]


def guardar(datos: dict, carpeta: Path) -> tuple[Path, Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    m = datos["metadatos"]
    casos = m.get("casos_evaluados")
    ruta_json, ruta_md = rutas(m["fecha"], carpeta, casos)
    for ruta in existentes(m["fecha"], carpeta, casos):
        raise FileExistsError(f"{ruta.name} ya existe: la evaluación se corre una sola vez.")
    ruta_json.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ruta_md.write_text(reporte_md(datos), encoding="utf-8")
    return ruta_json, ruta_md


def _mostrar(ruta: Path) -> Path:
    """La ruta relativa al proyecto si está dentro de él; si no, completa."""
    return ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluación del asistente (T-33).")
    parser.add_argument("--demo", action="store_true",
                        help="ensayo con el modo demo: sin APIs y sin guardar archivos")
    parser.add_argument("--casos", nargs="+", metavar="ID",
                        help="reevaluar solo estos casos (por ejemplo EV-24); se guarda aparte")
    args = parser.parse_args(argv)
    ids = sorted(set(args.casos), key=lambda i: (len(i), i)) if args.casos else None

    conjunto = json.loads(CONJUNTO.read_text(encoding="utf-8"))
    try:
        casos = elegir_casos(conjunto["casos"], ids)
    except ValueError as error:
        print(f"{error}. No se llamó a Gemini.")
        return 2

    hoy = hoy_costa_rica()
    if not args.demo:
        # Antes de cualquier solicitud a Gemini: si la evaluación de hoy ya existe,
        # se detiene sin gastar cuota (antes solo se revisaba al guardar, al final).
        ya = existentes(hoy.isoformat(), CARPETA_EVIDENCIAS, ids)
        if ya:
            que = "La reevaluación" if ids else "La evaluación"
            print(f"{que} de hoy ya existe ({', '.join(r.name for r in ya)}): "
                  "se corre una sola vez. No se llamó a Gemini.\n"
                  "Para un ensayo sin APIs use: python tests/evaluar.py --demo")
            return 1

    config = cargar_config()
    config = replace(config, modo_demo=args.demo, elevenlabs_api_key="")  # nunca audio
    if not args.demo:
        config.verificar_gemini()
    base = cargar_base()

    print(f"Evaluando {len(casos)} casos "
          f"{'en modo demo (sin APIs)' if args.demo else 'con Gemini real (sin audio)'}…\n")
    if args.demo:
        resultados = ejecutar(casos, base, config, hoy)
    else:
        with gemini_client.crear_cliente(config) as cliente:  # un cliente para todo (C-01)
            resultados = ejecutar(casos, base, config, hoy, cliente)

    datos = {
        "metadatos": {
            "fecha": hoy.isoformat(), "modelo": config.gemini_model,
            "temperatura": gemini_client.TEMPERATURA, "modo_demo": args.demo,
            "version_conjunto": conjunto["metadatos"]["version"],
            "version_base": base["metadatos"]["version"],
            "regla_numeros": "un término que empieza con dígito no puede ir pegado a otro dígito antes (\"5%\" no está en \"15%\")",
        },
        "resumen": resumen(resultados, conjunto["metadatos"], parcial=bool(ids)),
        "casos": resultados,
    }
    if ids:
        datos["metadatos"].update({
            "casos_evaluados": ids,
            "reevaluacion_de": evaluacion_original(CARPETA_EVIDENCIAS),
            "motivo": "plan alternativo de R-05: casos que fallaron, después del ciclo C-06",
        })
    print("\nResumen (comprobaciones automáticas):")
    for grupo in (*TIPOS, "hu01"):
        g = datos["resumen"][grupo]
        if g["total"] == 0:
            continue
        minimo = ("(mínimo: no aplica en una reevaluación parcial)" if g["cumple"] is None
                  else f"(mínimo {g['minimo']}) {'✅' if g['cumple'] else '❌'}")
        print(f"  {grupo:13s} {g['aprobados']:2d} de {g['total']:2d} {minimo}")
    if args.demo:
        print("\nModo demo: no se guardan archivos.")
        return 0
    ruta_json, ruta_md = guardar(datos, CARPETA_EVIDENCIAS)
    print(f"\nGuardado: {_mostrar(ruta_json)} y {_mostrar(ruta_md)}")
    print("Falta la revisión humana: abra el .md y marque cada caso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
