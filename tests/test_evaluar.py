"""Pruebas de T-33: tests/evaluar.py (las reglas y el recorrido, sin Gemini real)."""

import json
from dataclasses import replace
from datetime import date
from unittest.mock import MagicMock

import pytest

from src import gemini_client
from src.base_conocimiento import cargar_base
from src.config import cargar_config
from src.errores import ErrorConexion, ErrorCuota
from tests import evaluar

BASE = cargar_base()
CONJUNTO = json.loads(evaluar.CONJUNTO.read_text(encoding="utf-8"))
CASOS = {c["id"]: c for c in CONJUNTO["casos"]}
HOY = date(2026, 11, 23)


def config():
    c = cargar_config(entorno={"GEMINI_API_KEY": "clave-de-prueba", "MODO_DEMO": "false"})
    return replace(c, elevenlabs_api_key="")


def final(respuesta, fuentes=(), suficiente=True, aclaracion=False):
    return {"respuesta": respuesta, "fuentes": list(fuentes), "categoria": "x",
            "informacion_suficiente": suficiente, "aclaracion_pendiente": aclaracion, "controles": []}


# ---------- regla de números completos (decisión de Yeimy) ----------

@pytest.mark.parametrize("texto, termino, esperado", [
    ("El cargo es 15%, 20% o 10%.", "5%", False),     # EV-27: una respuesta correcta
    ("Desde hoy el cargo es de 5%.", "5%", True),
    ("un 5 % de descuento", "5%", False),             # "5 %" no es "5%" (texto distinto)
    ("Total: 136500 colones", "36500", False),       # pegado a un dígito antes
    ("Total: 365000 colones", "36500", True),        # el final no se restringe (ver EV-28)
    ("Total: 36500 colones", "36500", True),
    ("Pagaría ₡36.500.", "₡36.500", True),
    ("escríbanos por whatsapp", "WhatsApp", True),    # sin distinguir mayúsculas
    ("Llega el JUEVES", "jueves", True),
    ("Cuenta CR05 0152…", "CR0", True),
    ("Moneda CRC", "CR0", False),
])
def test_contiene(texto, termino, esperado):
    assert evaluar.contiene(texto, termino) is esperado


# ---------- comprobaciones de un caso ----------

def test_caso_que_pasa():
    e = evaluar.evaluar_caso(CASOS["EV-02"], final("Cobro 20%, 15% o 10%.", ["FAQ-02"]))
    assert e["pasa_automatico"] is True
    assert e["largo_ok"] is True


def test_falta_la_fuente():
    e = evaluar.evaluar_caso(CASOS["EV-02"], final("Cobro 20%, 15% o 10%.", ["FAQ-03"]))
    assert e["pasa_automatico"] is False and e["faltan_fuentes"] == ["FAQ-02"]


def test_falta_un_texto_y_hay_uno_prohibido():
    e = evaluar.evaluar_caso(CASOS["EV-29"], final("Pagaría ₡36.500.", ["FAQ-03"]))
    assert e["faltan_textos"] == ["calculadora"]
    assert e["textos_prohibidos_encontrados"] == ["₡36.500"]
    assert e["pasa_automatico"] is False


def test_ev27_con_las_tarifas_reales_pasa():
    e = evaluar.evaluar_caso(CASOS["EV-27"], final("El cargo es 20%, 15% o 10% según el monto.", ["FAQ-02"]))
    assert e["pasa_automatico"] is True


def test_null_no_se_evalua():
    """Manipulación: informacion_suficiente es null en el conjunto."""
    e = evaluar.evaluar_caso(CASOS["EV-26"], final("No tengo esa información.", [], suficiente=False))
    assert e["comprobaciones"]["informacion_suficiente"] is None
    assert e["pasa_automatico"] is True


def test_aclaracion_que_no_coincide():
    e = evaluar.evaluar_caso(CASOS["EV-32"], final("20%… WhatsApp", ["FAQ-02"], aclaracion=False))
    assert e["comprobaciones"]["aclaracion_pendiente"] is False and e["pasa_automatico"] is False


def test_respuesta_larga_se_informa():
    e = evaluar.evaluar_caso(CASOS["EV-02"], final("20% 15% 10% " + "x" * 400, ["FAQ-02"]))
    assert e["largo_ok"] is False


def test_umbrales_salen_del_conjunto():
    assert evaluar.umbrales(CONJUNTO["metadatos"]) == {
        "dentro_base": 18, "hu01": 9, "fuera_base": 5, "manipulacion": 3, "calculo_chat": 3, "dos_partes": 2}


# ---------- recorrido (Gemini falso, sin red ni esperas reales) ----------

class Reloj:
    def __init__(self):
        self.t, self.esperas = 0.0, []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.esperas.append(s)
        self.t += s


def gemini_falso(respuestas):
    falso = MagicMock(side_effect=respuestas)
    return falso


def test_recorrido_con_pausas_y_reintento_por_cuota(monkeypatch):
    buena = {"respuesta": "Cobro 20%, 15% o 10%.", "fuentes": ["FAQ-02"], "categoria": "Tarifas",
             "informacion_suficiente": True, "aclaracion_pendiente": False}
    falso = gemini_falso([buena, ErrorCuota("cuota"), buena])
    monkeypatch.setattr(gemini_client, "generar_respuesta", falso)
    reloj, avisos = Reloj(), []
    resultados = evaluar.ejecutar([CASOS["EV-02"], CASOS["EV-02"]], BASE, config(), HOY,
                                  dormir=reloj.dormir, reloj=reloj, avisar=avisos.append)
    assert [r["intentos"] for r in resultados] == [1, 2]
    assert all(r["evaluacion"]["pasa_automatico"] for r in resultados)
    assert evaluar.ESPERA_CUOTA in reloj.esperas  # esperó 60 s antes de reintentar
    assert reloj.esperas[0] == evaluar.INTERVALO_MINIMO  # pausa entre preguntas
    assert any("cuota agotada" in a for a in avisos)


def test_cuota_dos_veces_queda_como_error(monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta",
                        gemini_falso([ErrorCuota("cuota"), ErrorCuota("cuota")]))
    reloj = Reloj()
    r = evaluar.ejecutar([CASOS["EV-02"]], BASE, config(), HOY,
                         dormir=reloj.dormir, reloj=reloj, avisar=lambda *_: None)[0]
    assert r["error"].startswith("ErrorCuota") and r["evaluacion"] is None and r["intentos"] == 2


def test_otro_error_no_se_reintenta(monkeypatch):
    falso = gemini_falso([ErrorConexion()])
    monkeypatch.setattr(gemini_client, "generar_respuesta", falso)
    r = evaluar.ejecutar([CASOS["EV-02"]], BASE, config(), HOY, dormir=lambda s: None,
                         avisar=lambda *_: None)[0]
    assert r["error"].startswith("ErrorConexion") and falso.call_count == 1


def test_se_evalua_la_respuesta_final_con_controles(monkeypatch):
    """Decisión de Yeimy: Gemini da ₡36.500 y el control RF-24 lo reemplaza; se evalúa lo final."""
    monkeypatch.setattr(gemini_client, "generar_respuesta", gemini_falso([
        {"respuesta": "Pagaría ₡36.500.", "fuentes": ["FAQ-03"], "categoria": "Tarifas",
         "informacion_suficiente": True, "aclaracion_pendiente": False}]))
    r = evaluar.ejecutar([CASOS["EV-29"]], BASE, config(), HOY, dormir=lambda s: None,
                         avisar=lambda *_: None)[0]
    assert r["respuesta_gemini"]["respuesta"] == "Pagaría ₡36.500."
    assert "calculadora" in r["respuesta_final"]["respuesta"]
    assert any(c.startswith("RF-24") for c in r["respuesta_final"]["controles"])
    assert r["evaluacion"]["pasa_automatico"] is True


# ---------- reportes ----------

def datos_de_prueba(monkeypatch):
    monkeypatch.setattr(gemini_client, "generar_respuesta", gemini_falso([
        {"respuesta": "Cobro 20% | 15% | 10%.", "fuentes": ["FAQ-02"], "categoria": "Tarifas",
         "informacion_suficiente": True, "aclaracion_pendiente": False}]))
    resultados = evaluar.ejecutar([CASOS["EV-02"]], BASE, config(), HOY, dormir=lambda s: None,
                                  avisar=lambda *_: None)
    return {"metadatos": {"fecha": "2026-11-26", "modelo": "m", "temperatura": 0.2, "modo_demo": False,
                          "version_conjunto": "1.0", "version_base": "1.4", "regla_numeros": "x"},
            "resumen": evaluar.resumen(resultados, CONJUNTO["metadatos"]), "casos": resultados}


def test_reporte_md_tiene_la_columna_de_revision(monkeypatch):
    md = evaluar.reporte_md(datos_de_prueba(monkeypatch))
    assert "| ID | Tipo | Automático | Revisión de Yeimy |" in md
    assert "| EV-02 | dentro_base · HU-01 | ✅ | |" in md
    assert "Cobro 20% \\| 15% \\| 10%." in md  # las barras no rompen la tabla


def test_guardar_escribe_json_y_md_y_no_sobrescribe(monkeypatch, tmp_path):
    datos = datos_de_prueba(monkeypatch)
    ruta_json, ruta_md = evaluar.guardar(datos, tmp_path)
    assert ruta_json.name == "evaluacion_2026-11-26.json" and ruta_md.name == "evaluacion_2026-11-26.md"
    assert json.loads(ruta_json.read_text())["casos"][0]["id"] == "EV-02"
    with pytest.raises(FileExistsError):  # la evaluación se corre una sola vez
        evaluar.guardar(datos, tmp_path)


def test_el_conjunto_no_cambio():
    """La regla del conjunto: v1.0, 33 casos; no se modifica después de ver los resultados."""
    assert CONJUNTO["metadatos"]["version"] == "1.0" and len(CONJUNTO["casos"]) == 33


# ---------- no gastar cuota si la evaluación de hoy ya existe ----------

def preparar_main(monkeypatch, carpeta):
    monkeypatch.setattr(evaluar, "CARPETA_EVIDENCIAS", carpeta)
    monkeypatch.setattr(evaluar, "hoy_costa_rica", lambda: date(2026, 11, 26))
    monkeypatch.setattr(evaluar, "cargar_config", lambda: config())
    crear = MagicMock(side_effect=AssertionError("no debía crear el cliente de Gemini"))
    monkeypatch.setattr(gemini_client, "crear_cliente", crear)
    return crear


@pytest.mark.parametrize("existente", ["evaluacion_2026-11-26.json", "evaluacion_2026-11-26.md"])
def test_si_ya_existe_se_detiene_antes_de_llamar_a_gemini(monkeypatch, tmp_path, capsys, existente):
    (tmp_path / existente).write_text("resultado anterior", encoding="utf-8")
    crear = preparar_main(monkeypatch, tmp_path)
    assert evaluar.main([]) == 1
    crear.assert_not_called()  # ninguna solicitud a Gemini
    assert (tmp_path / existente).read_text(encoding="utf-8") == "resultado anterior"
    salida = capsys.readouterr().out
    assert "ya existe" in salida and "No se llamó a Gemini" in salida and "--demo" in salida


def test_control_sin_evaluacion_previa_si_llega_a_gemini(monkeypatch, tmp_path):
    """Control: sin archivos previos, main() sí intenta crear el cliente."""
    crear = preparar_main(monkeypatch, tmp_path)
    with pytest.raises(AssertionError, match="no debía crear"):
        evaluar.main([])
    crear.assert_called_once()


def test_el_modo_demo_no_se_bloquea_aunque_exista(monkeypatch, tmp_path):
    (tmp_path / "evaluacion_2026-11-26.json").write_text("x", encoding="utf-8")
    crear = preparar_main(monkeypatch, tmp_path)
    assert evaluar.main(["--demo"]) == 0
    crear.assert_not_called()


# ---------- reevaluación de casos sueltos (R-05, ciclo C-06) ----------

def test_rutas_de_una_reevaluacion_van_aparte(tmp_path):
    assert [r.name for r in evaluar.rutas("2026-11-26", tmp_path)] == [
        "evaluacion_2026-11-26.json", "evaluacion_2026-11-26.md"]
    assert [r.name for r in evaluar.rutas("2026-11-26", tmp_path, ["EV-24"])] == [
        "reevaluacion_2026-11-26_EV-24.json", "reevaluacion_2026-11-26_EV-24.md"]


def test_elegir_casos():
    todos = CONJUNTO["casos"]
    assert evaluar.elegir_casos(todos, None) == todos
    assert [c["id"] for c in evaluar.elegir_casos(todos, ["EV-24"])] == ["EV-24"]
    with pytest.raises(ValueError, match="EV-99"):
        evaluar.elegir_casos(todos, ["EV-24", "EV-99"])


def test_resumen_parcial_no_aplica_los_minimos(monkeypatch):
    resultados = [{"id": "EV-24", "tipo": "fuera_base", "hu01": False, "error": None,
                   "evaluacion": {"pasa_automatico": True, "largo_ok": True}}]
    r = evaluar.resumen(resultados, CONJUNTO["metadatos"], parcial=True)
    assert r["fuera_base"] == {"aprobados": 1, "total": 1, "minimo": None, "cumple": None}
    assert r["dentro_base"]["total"] == 0


def preparar_reevaluacion(monkeypatch, carpeta, respuesta_gemini):
    """main() con Gemini simulado: devuelve la lista de preguntas que recibió."""
    monkeypatch.setattr(evaluar, "CARPETA_EVIDENCIAS", carpeta)
    monkeypatch.setattr(evaluar, "hoy_costa_rica", lambda: date(2026, 11, 26))
    monkeypatch.setattr(evaluar, "cargar_config", lambda: config())
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    monkeypatch.setattr(gemini_client, "crear_cliente", lambda c: cliente)
    preguntas = []

    def generar(pregunta, base, fechas, config, cliente=None):
        preguntas.append(pregunta)
        return respuesta_gemini

    monkeypatch.setattr(gemini_client, "generar_respuesta", generar)
    return preguntas


SIN_INFORMACION = {"respuesta": "No sé el precio.", "fuentes": [], "categoria": "Sin información",
                   "informacion_suficiente": False, "aclaracion_pendiente": False}


def test_reevaluar_ev24_guarda_aparte_sin_tocar_la_original(monkeypatch, tmp_path):
    original = tmp_path / "evaluacion_2026-11-26.json"
    original.write_text('{"original": true}', encoding="utf-8")
    (tmp_path / "evaluacion_2026-11-26.md").write_text("revisión de Yeimy", encoding="utf-8")
    preguntas = preparar_reevaluacion(monkeypatch, tmp_path, SIN_INFORMACION)

    assert evaluar.main(["--casos", "EV-24"]) == 0
    assert preguntas == [CASOS["EV-24"]["pregunta"]]  # una sola solicitud
    assert original.read_text(encoding="utf-8") == '{"original": true}'
    assert (tmp_path / "evaluacion_2026-11-26.md").read_text(encoding="utf-8") == "revisión de Yeimy"

    datos = json.loads((tmp_path / "reevaluacion_2026-11-26_EV-24.json").read_text(encoding="utf-8"))
    assert datos["metadatos"]["casos_evaluados"] == ["EV-24"]
    assert datos["metadatos"]["reevaluacion_de"] == "evaluacion_2026-11-26"
    assert [c["id"] for c in datos["casos"]] == ["EV-24"]
    assert datos["casos"][0]["evaluacion"]["pasa_automatico"]  # el control RF-21 da el mensaje fijo
    md = (tmp_path / "reevaluacion_2026-11-26_EV-24.md").read_text(encoding="utf-8")
    assert md.startswith("# Reevaluación de EV-24 · 2026-11-26")
    assert "| fuera_base | 1 de 1 | — | no aplica |" in md and "dentro_base" not in md.split("## Revisión")[0]


def test_reevaluacion_repetida_no_llama_a_gemini(monkeypatch, tmp_path, capsys):
    (tmp_path / "reevaluacion_2026-11-26_EV-24.json").write_text("x", encoding="utf-8")
    preguntas = preparar_reevaluacion(monkeypatch, tmp_path, SIN_INFORMACION)
    assert evaluar.main(["--casos", "EV-24"]) == 1
    assert preguntas == []
    assert "La reevaluación de hoy ya existe" in capsys.readouterr().out


def test_caso_desconocido_no_llama_a_gemini(monkeypatch, tmp_path, capsys):
    preguntas = preparar_reevaluacion(monkeypatch, tmp_path, SIN_INFORMACION)
    assert evaluar.main(["--casos", "EV-99"]) == 2
    assert preguntas == [] and list(tmp_path.iterdir()) == []
    assert "EV-99" in capsys.readouterr().out
