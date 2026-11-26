"""Pruebas de T-25: app.py con el probador de Streamlit (AppTest).

Corren en modo demo: no llaman a Gemini ni a ElevenLabs. Los casos de error
reemplazan ``responder`` por una función falsa.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import asistente, base_conocimiento
from src.errores import ErrorBaseConocimiento, ErrorConexion

TIEMPO = 30
APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def modo_demo(monkeypatch):
    monkeypatch.setenv("MODO_DEMO", "true")


def abrir():
    return AppTest.from_file(APP, default_timeout=TIEMPO).run()


def htmls(at):
    """El HTML visible de la página (sin la hoja de estilos)."""
    return "\n".join(h.proto.body for h in at.html if not h.proto.body.lstrip().startswith("<style>"))


def preguntar(at, texto):
    at.text_input(key="campo_pregunta").input(texto)
    at.button(key="enviar").click()
    return at.run()


# ---------- la app abre (evidencia de T-25) ----------

def test_la_app_abre_con_la_estructura_de_d13():
    at = abrir()
    assert not at.exception
    pagina = htmls(at)
    assert "Tu Personal Shopper" in pagina
    assert "Próxima compra:" in pagina or "aún no está definida" in pagina  # D-14
    assert "¿Necesita información de nuestro servicio?" in pagina
    assert "¡Yo te lo compro!" in pagina
    assert [t.label.split()[-1] for t in at.tabs] == ["Preguntar", "Estimar", "Historial"]
    assert [b.label for b in at.button] == [
        "¿Cuánto cobran?", "¿Número de SINPE?", "¿Próxima compra?", "Enviar"]


# ---------- RF-01 y RF-08: pregunta escrita, respuesta, fuente y categoría ----------

def test_pregunta_escrita_muestra_respuesta_fuente_y_categoria():
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    assert not at.exception
    pagina = htmls(at)
    assert 'class="ps-pregunta">¿A qué número hago el SINPE?<' in pagina
    assert "8888-0000" in pagina
    assert "Fuente: FAQ-14" in pagina
    assert ">Pagos<" in pagina
    assert "¿Necesita información" not in pagina  # el saludo se oculta al responder
    assert at.text_input(key="campo_pregunta").value == ""  # el campo se limpia


@pytest.mark.parametrize("indice, fuente", [(0, "FAQ-02"), (1, "FAQ-14"), (2, "CALENDARIO")])
def test_preguntas_rapidas_pasan_por_el_mismo_flujo(indice, fuente):
    at = abrir()
    at.button(key=f"rapida_{indice}").click()
    at.run()
    assert not at.exception
    assert f"Fuente: {fuente}" in htmls(at)


def test_solo_se_ve_la_ultima_pregunta():
    """Decisión de Yeimy: la pestaña Preguntar muestra solo la última conversación."""
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    at = preguntar(at, "¿Venden ropa?")
    pagina = htmls(at)
    assert "¿Venden ropa?" in pagina
    assert "¿A qué número hago el SINPE?" not in pagina
    assert "Fuente:" not in pagina  # RF-21: sin fuente
    assert "Sin información" in pagina


def test_pregunta_vacia_muestra_el_aviso_sin_responder():
    at = preguntar(abrir(), "   ")
    assert not at.exception
    assert any("Escriba una pregunta" in c.value for c in at.caption)
    assert "ps-respuesta" not in htmls(at)


def test_una_pregunta_con_codigo_no_se_ejecuta():
    """D-17: el texto del cliente se escapa antes de mostrarlo."""
    at = preguntar(abrir(), "<script>alert(1)</script> ¿SINPE?")
    pagina = htmls(at)
    assert "<script>alert(1)</script>" not in pagina
    assert "&lt;script&gt;" in pagina


# ---------- RF-31: controles desactivados mientras se procesa ----------

def test_mientras_procesa_enviar_y_las_preguntas_rapidas_estan_desactivados(monkeypatch):
    """La respuesta falsa se detiene a la mitad: la pantalla queda como se ve mientras procesa."""
    def detener(*args, **kwargs):
        raise RuntimeError("detenido a mitad del proceso")

    monkeypatch.setattr(asistente, "responder", detener)
    at = abrir()
    assert all(not b.disabled for b in at.button)
    at.button(key="rapida_1").click()
    at.run()
    assert all(b.disabled for b in at.button)
    assert at.text_input(key="campo_pregunta").disabled


def test_despues_de_responder_los_controles_se_vuelven_a_activar():
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    assert all(not b.disabled for b in at.button)
    assert not at.text_input(key="campo_pregunta").disabled


# ---------- errores (sección 7) ----------

def test_error_de_gemini_muestra_el_mensaje_amigable(monkeypatch):
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: (_ for _ in ()).throw(ErrorConexion()))
    at = preguntar(abrir(), "¿Cómo pago?")
    assert not at.exception
    assert [e.value for e in at.error] == [str(ErrorConexion())]
    assert all(not b.disabled for b in at.button)


def test_base_danada_muestra_el_mensaje_y_la_app_no_se_cierra(monkeypatch):
    def falla():
        raise ErrorBaseConocimiento(detalle_tecnico="data/base_conocimiento.json no existe")

    monkeypatch.setattr(base_conocimiento, "cargar_base", falla)
    at = abrir()
    assert not at.exception
    assert [e.value for e in at.error] == [str(ErrorBaseConocimiento())]
    assert "data/base" not in at.error[0].value
    assert not at.tabs  # el chat no se muestra


def test_la_consola_no_registra_la_pregunta(caplog):
    with caplog.at_level("DEBUG", logger="personal_shopper"):
        preguntar(abrir(), "Mi pregunta privada sobre el SINPE")
    assert "Mi pregunta privada" not in caplog.text  # RNF-15
