"""Pruebas de T-25: app.py con el probador de Streamlit (AppTest).

Corren en modo demo: no llaman a Gemini ni a ElevenLabs. Los casos de error
reemplazan ``responder`` por una función falsa.
"""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import asistente, base_conocimiento
from src.calculadora import ZONA_PUNTO_ENTREGA
from src.validacion import MENSAJE_MONTO_INVALIDO
from src.errores import (
    MENSAJE_AUDIO_DEMO,
    MENSAJE_CUOTA_AUDIO,
    MENSAJE_CUOTA_GEMINI,
    MENSAJE_SERVICIO_NO_DISPONIBLE,
    ErrorBaseConocimiento,
    ErrorConexion,
    ErrorConfiguracion,
    ErrorCuota,
    ErrorServicio,
)

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


def en_preguntar(at):
    """La pestaña Preguntar (el historial repite preguntas y audios en su propia pestaña)."""
    return at.tabs[0]


def html_preguntar(at):
    return "\n".join(h.proto.body for h in en_preguntar(at).get("html"))


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
    assert [t.label.split(" ", 1)[1] for t in at.tabs] == ["Preguntar", "Estimar", "Historial (0)"]
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
    pagina = html_preguntar(at)
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

def test_error_de_gemini_muestra_el_aviso_amigable(monkeypatch):
    """T-29: burbuja de aviso; "sin conexión" no lleva WhatsApp (no abriría)."""
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: (_ for _ in ()).throw(ErrorConexion()))
    at = preguntar(abrir(), "¿Cómo pago?")
    assert not at.exception and not at.error
    assert f'class="ps-aviso">⚠️ {ErrorConexion()}<' in html_preguntar(at)
    assert not en_preguntar(at).get("link_button")
    assert all(not b.disabled for b in at.button)


@pytest.mark.parametrize("error", [ErrorCuota(MENSAJE_CUOTA_GEMINI), ErrorServicio(MENSAJE_SERVICIO_NO_DISPONIBLE),
                                   ErrorConfiguracion()])
def test_errores_que_mencionan_whatsapp_llevan_el_boton(monkeypatch, error):
    """Decisión de Yeimy (T-29)."""
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: (_ for _ in ()).throw(error))
    at = preguntar(abrir(), "¿Cómo pago?")
    assert str(error) in html_preguntar(at)
    botones = en_preguntar(at).get("link_button")
    assert [b.proto.label for b in botones] == ["Escribir por WhatsApp"]
    assert botones[0].proto.url.startswith("https://wa.me/50688880000?text=")


def test_cuota_agotada_sugiere_el_modo_demo_en_la_consola(monkeypatch, caplog):
    """Sección 7: "Se sugiere activar MODO_DEMO para la demostración" (para la dueña)."""
    monkeypatch.setattr(asistente, "responder",
                        lambda *a, **k: (_ for _ in ()).throw(ErrorCuota(MENSAJE_CUOTA_GEMINI)))
    with caplog.at_level("WARNING", logger="personal_shopper"):
        preguntar(abrir(), "¿Cómo pago?")
    assert "MODO_DEMO=true" in caplog.text


def test_base_danada_muestra_encabezado_aviso_whatsapp_y_pie(monkeypatch):
    """Sección 7 y decisión de Yeimy (T-29): la app no se cierra."""
    def falla():
        raise ErrorBaseConocimiento(detalle_tecnico="data/base_conocimiento.json no existe")

    monkeypatch.setattr(base_conocimiento, "cargar_base", falla)
    at = abrir()
    assert not at.exception and not at.error
    pagina = htmls(at)
    assert "Tu Personal Shopper" in pagina and "¡Yo te lo compro!" in pagina
    assert str(ErrorBaseConocimiento()) in pagina
    assert "data/base" not in pagina  # el detalle técnico solo va a la consola
    assert [b.proto.label for b in at.get("link_button")] == ["Escribir por WhatsApp"]
    assert not at.tabs  # sin base no hay chat ni calculadora


# ---------- T-29: modo demostración (RF-20, D-18) ----------

def test_modo_demo_muestra_la_etiqueta_y_la_franja():
    pagina = htmls(abrir())
    assert 'class="ps-demo">DEMO<' in pagina
    assert "Modo demostración: las respuestas son simuladas." in pagina


def test_sin_modo_demo_no_hay_etiqueta_ni_franja(monkeypatch):
    monkeypatch.setenv("MODO_DEMO", "false")
    pagina = htmls(abrir())
    assert "DEMO<" not in pagina
    assert "las respuestas son simuladas" not in pagina


def test_la_consola_no_registra_la_pregunta(caplog):
    with caplog.at_level("DEBUG", logger="personal_shopper"):
        preguntar(abrir(), "Mi pregunta privada sobre el SINPE")
    assert "Mi pregunta privada" not in caplog.text  # RNF-15


# ---------- T-26: reproductor, aviso y WhatsApp ----------

def respuesta(**cambios):
    """Un resultado de ``responder()`` con audio (formato de T-23)."""
    base = {"respuesta": "Puede pagar por SINPE Móvil al 8888-0000.", "fuentes": ["FAQ-14"],
            "categoria": "Pagos", "informacion_suficiente": True, "aclaracion_pendiente": False,
            "recortado": False, "controles": [], "modo_demo": False,
            "audio": b"ID3-audio-falso", "audio_desde_cache": False, "aviso_audio": None}
    return {**base, **cambios}


def con_respuesta(monkeypatch, resultado):
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: resultado)
    return preguntar(abrir(), "¿Cómo pago?")


def test_respuesta_con_reproductor_que_no_suena_solo(monkeypatch):
    at = con_respuesta(monkeypatch, respuesta())
    reproductores = en_preguntar(at).get("audio")
    assert len(reproductores) == 1
    assert reproductores[0].proto.url.endswith(".mp3")
    assert not reproductores[0].proto.autoplay  # D-03
    assert not at.get("link_button")


def test_sin_audio_se_muestra_el_aviso(monkeypatch):
    """RF-19: el texto se muestra igual, con el aviso en lugar del reproductor."""
    at = con_respuesta(monkeypatch, respuesta(audio=None, aviso_audio=MENSAJE_CUOTA_AUDIO))
    assert not at.get("audio")
    assert MENSAJE_CUOTA_AUDIO in htmls(at)
    assert "SINPE Móvil al 8888-0000" in htmls(at)


def test_modo_demo_muestra_el_aviso_de_demo_en_lugar_del_reproductor():
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    assert not at.get("audio")
    assert MENSAJE_AUDIO_DEMO in htmls(at)  # D-18
    assert not at.get("link_button")


def test_sin_informacion_boton_de_whatsapp_en_lugar_del_audio():
    """D-15 (en modo demo, con la pregunta real fuera de la base)."""
    at = preguntar(abrir(), "¿Venden ropa?")
    assert not at.get("audio")
    assert MENSAJE_AUDIO_DEMO not in htmls(at)
    botones = at.get("link_button")
    assert [b.proto.label for b in botones] == ["Escribir por WhatsApp"]
    assert botones[0].proto.url.startswith("https://wa.me/50688880000?text=Hola")
    assert "ropa" not in botones[0].proto.url  # la pregunta no viaja en el enlace


def test_dos_partes_audio_y_boton_de_whatsapp(monkeypatch):
    at = con_respuesta(monkeypatch, respuesta(aclaracion_pendiente=True))
    assert len(en_preguntar(at).get("audio")) == 1
    assert len(at.get("link_button")) == 1


# ---------- T-27: pestaña Estimar (RF-13 a RF-16, D-16) ----------

def estimar(at, monto=None, zona=None, primera=None):
    if monto is not None:
        at.text_input(key="monto").input(monto)
    if zona is not None:
        at.selectbox(key="zona").select(zona)
    if primera is not None:
        at.checkbox(key="primera_compra").check() if primera else at.checkbox(key="primera_compra").uncheck()
    return at.run()


def avisos_rojos(at):
    return [c.value for c in at.caption if c.value.startswith(":red[")]


def test_estimar_empieza_vacio_sin_desglose_ni_error():
    """Decisión de Yeimy: el formulario empieza vacío."""
    at = abrir()
    assert at.text_input(key="monto").value == ""
    assert at.selectbox(key="zona").value == ZONA_PUNTO_ENTREGA
    assert at.checkbox(key="primera_compra").value is False
    assert "Total estimado" not in htmls(at)
    assert not avisos_rojos(at)
    assert "ps-activo" not in htmls(at)  # ninguna tarjeta resaltada


def test_la_lista_de_zonas_es_una_sola_con_el_costo_en_el_nombre():
    """RF-13 y D-16."""
    at = abrir()
    opciones = at.selectbox(key="zona").options
    assert opciones[0] == ZONA_PUNTO_ENTREGA
    assert "La Trocha (+₡2.000)" in opciones
    assert "Pinares" in opciones or any(o.endswith("Pinares") for o in opciones)
    assert not any("(+" in o for o in opciones if "Trocha" not in o and "Buenos Aires" not in o
                   and "Jiménez" not in o and "La Granja" not in o)


def test_caso_de_la_evidencia_30000_en_la_trocha():
    at = estimar(abrir(), "₡30.000", "La Trocha")
    pagina = htmls(at)
    assert "Servicio (15%)" in pagina and "₡4.500" in pagina and "₡2.000" in pagina
    assert "₡36.500" in pagina
    assert "Este es un estimado." in pagina  # RF-15
    assert pagina.count("ps-activo") == 1 and "15%" in pagina.split("ps-activo")[1][:400]


@pytest.mark.parametrize("monto, zona, primera, total", [
    ("10000", "Cuadrante", False, "₡12.000"),
    ("15000", "Cuadrante", False, "₡17.250"),
    ("30000", "La Trocha", False, "₡36.500"),
    ("40000", "Cuadrante", False, "₡46.000"),
    ("50000", "Cuadrante", False, "₡55.000"),
    ("30000", "Cuadrante", True, "₡30.000"),
    ("30000", "Buenos Aires", True, "₡30.000"),
])
def test_casos_de_referencia_de_la_seccion_53(monto, zona, primera, total):
    at = estimar(abrir(), monto, zona, primera)
    pagina = htmls(at)
    assert f'class="ps-total-monto">{total}<' in pagina


@pytest.mark.parametrize("monto", ["30000", "30.000", "₡30.000", "₡ 30.000"])
def test_el_monto_acepta_varios_formatos(monto):
    assert "₡36.500" in htmls(estimar(abrir(), monto, "La Trocha"))


@pytest.mark.parametrize("monto", ["abc", "0", "-5", "₡"])
def test_monto_invalido_muestra_el_mensaje_sin_calcular(monto):
    """RF-16."""
    at = estimar(abrir(), monto)
    assert avisos_rojos(at) == [f":red[{MENSAJE_MONTO_INVALIDO}]"]
    assert "Total estimado" not in htmls(at)
    assert "ps-activo" not in htmls(at)


def test_primera_compra_muestra_la_cortesia():
    at = estimar(abrir(), "30000", "La Trocha", True)
    pagina = htmls(at)
    assert "Cortesía de bienvenida" in pagina
    assert 'class="ps-total-monto">₡30.000<' in pagina


def test_cambiar_la_zona_recalcula_sin_boton():
    """D-16: sin botón Calcular."""
    at = estimar(abrir(), "30000", "La Trocha")
    assert "₡36.500" in htmls(at)
    at = estimar(at, zona="Cuadrante")
    assert 'class="ps-total-monto">₡34.500<' in htmls(at)
    assert not any(b.label == "Calcular" for b in at.button)


def test_la_calculadora_funciona_aunque_gemini_falle(monkeypatch):
    """Spec 4.3: no llama a ninguna API."""
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: (_ for _ in ()).throw(ErrorConexion()))
    at = preguntar(abrir(), "¿Cómo pago?")
    at = estimar(at, "30000", "La Trocha")
    assert "₡36.500" in htmls(at)



def test_la_app_inserta_el_script_de_idioma():
    """Ajuste de T-27: Chrome no debe traducir la página (cambiaba "cargo" por "carga")."""
    at = abrir()
    assert any('raiz.lang = "es"' in h.proto.body for h in at.html)


# ---------- T-28: pestaña Historial (RF-17, RNF-15) ----------

def en_historial(at):
    return at.tabs[2]


def html_historial(at):
    return "\n".join(h.proto.body for h in en_historial(at).get("html"))


def test_historial_empieza_vacio():
    at = abrir()
    assert at.tabs[2].label.endswith("Historial (0)")
    assert "Sus preguntas de esta sesión aparecerán aquí." in html_historial(at)
    assert "Se borra al cerrar o recargar la página." in html_historial(at)


def test_despues_de_6_consultas_se_ven_todas_de_la_mas_nueva_a_la_mas_vieja():
    """Prueba de aceptación de RF-17 (spec, sección 11) y decisión de Yeimy: todas."""
    preguntas = ["¿A qué número hago el SINPE?", "¿Cuánto cobran?", "¿Cuándo es la próxima compra?",
                 "¿Venden ropa?", "¿Entregan en Pinares?", "¿Cómo pago?"]
    at = abrir()
    for p in preguntas:
        at = preguntar(at, p)
    assert at.tabs[2].label.endswith("Historial (6)")
    pagina = html_historial(at)
    posiciones = [pagina.index(f'ps-consulta-pregunta">{p}<') for p in preguntas]
    assert posiciones == sorted(posiciones, reverse=True)  # la última pregunta va primero
    assert "Sus preguntas de esta sesión" not in pagina


def test_cada_consulta_tiene_lo_que_pide_rf17():
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    pagina = html_historial(at)
    assert re.search(r'class="ps-meta"><span>\d{1,2}:\d{2} [ap]\. m\.</span><span>Pagos · FAQ-14</span>', pagina)
    assert "8888-0000" in pagina  # la respuesta
    assert "Modo demo: sin audio" in pagina  # estado del audio


def test_consulta_con_audio_tiene_su_reproductor_en_el_historial(monkeypatch):
    """Decisión de Yeimy: estado y reproductor (desde la memoria, sin gastar créditos)."""
    at = con_respuesta(monkeypatch, respuesta())
    assert "🔊 Con audio" in html_historial(at)
    reproductores = en_historial(at).get("audio")
    assert len(reproductores) == 1 and not reproductores[0].proto.autoplay


def test_error_del_servicio_se_guarda_como_sin_respuesta(monkeypatch):
    """Spec, sección 7."""
    monkeypatch.setattr(asistente, "responder", lambda *a, **k: (_ for _ in ()).throw(ErrorConexion()))
    at = preguntar(abrir(), "¿Cómo pago?")
    pagina = html_historial(at)
    assert at.tabs[2].label.endswith("Historial (1)")
    assert 'ps-consulta-respuesta">Sin respuesta<' in pagina


def test_pregunta_invalida_no_se_guarda():
    """Decisión de Yeimy: las preguntas que no pasan la validación no son consultas."""
    at = preguntar(abrir(), "   ")
    assert at.tabs[2].label.endswith("Historial (0)")


def test_el_historial_es_de_la_sesion_y_no_se_guarda_en_disco(tmp_path, monkeypatch):
    """RNF-15: una sesión nueva (recargar la página) empieza vacía; nada se escribe en disco."""
    monkeypatch.chdir(tmp_path)
    at = preguntar(abrir(), "¿A qué número hago el SINPE?")
    assert at.tabs[2].label.endswith("Historial (1)")
    assert list(tmp_path.iterdir()) == []
    nueva = abrir()
    assert nueva.tabs[2].label.endswith("Historial (0)")


def test_la_pregunta_del_historial_se_escapa():
    at = preguntar(abrir(), "<b>hola</b> ¿SINPE?")
    assert "<b>hola</b>" not in html_historial(at)

