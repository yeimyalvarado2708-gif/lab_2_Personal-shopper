"""Excepciones propias del asistente (spec, sección 7; RF-18).

Cada excepción lleva dos textos separados:

- ``mensaje_usuario``: lo que ve el cliente. Sencillo, en español, sin claves,
  archivos, variables ni trazas, y con salida a WhatsApp cuando el cliente no
  puede resolver el problema.
- ``detalle_tecnico``: lo que se escribe en la consola para la dueña. Puede
  nombrar variables o archivos, pero NUNCA incluye el valor de una clave.

``str(error)`` devuelve siempre el mensaje para el usuario, para que un
``st.error(str(e))`` nunca muestre detalles técnicos por accidente.
"""

# Mensajes fijos para el cliente (spec, sección 7).
MENSAJE_NO_DISPONIBLE = (
    "En este momento el asistente no está disponible. "
    "Escríbanos por WhatsApp al 8888-0000 y con gusto le ayudamos."
)
MENSAJE_SIN_CONEXION = (
    "No hay conexión a internet en este momento. Intente de nuevo en unos minutos."
)
MENSAJE_CUOTA_GEMINI = (
    "El asistente alcanzó su límite de uso por ahora. "
    "Intente más tarde o escriba por WhatsApp al 8888-0000."
)
MENSAJE_RESPUESTA_INVALIDA = (
    "No se pudo generar una respuesta. Intente reformular su pregunta."
)
# Decisión de Yeimy (2026-11-25, T-18): cuando el servicio falla (500/503),
# reformular la pregunta no ayuda; se pide esperar o escribir por WhatsApp.
MENSAJE_SERVICIO_NO_DISPONIBLE = (
    "El asistente no pudo responder en este momento. "
    "Intente de nuevo en unos minutos o escríbanos por WhatsApp al 8888-0000."
)
MENSAJE_SOLO_TEXTO ="Por ahora la respuesta está disponible solo en texto."
MENSAJE_AUDIO_NO_DISPONIBLE = "El audio no está disponible en este momento."
# Decisión de Yeimy (2026-11-25, T-23): aviso en lugar del reproductor en
# modo demo (RF-20).
MENSAJE_AUDIO_DEMO = "Modo demostración: el audio no está disponible."
MENSAJE_CUOTA_AUDIO = (
    "Se agotaron los créditos de audio de este mes. "
    "La respuesta se muestra solo en texto."
)


class ErrorAsistente(Exception):
    """Base de todas las excepciones propias del asistente."""

    mensaje_por_defecto = MENSAJE_NO_DISPONIBLE

    def __init__(self, mensaje_usuario: str | None = None, detalle_tecnico: str = ""):
        self.mensaje_usuario = mensaje_usuario or self.mensaje_por_defecto
        self.detalle_tecnico = detalle_tecnico
        super().__init__(self.mensaje_usuario)

    def __str__(self) -> str:
        return self.mensaje_usuario


class ErrorValidacion(ErrorAsistente):
    """Entrada del usuario inválida (pregunta o monto). No se llama a ninguna API."""

    mensaje_por_defecto = "Revise los datos ingresados."


class ErrorBaseConocimiento(ErrorAsistente):
    """La base de conocimiento falta o está mal formada."""

    mensaje_por_defecto = MENSAJE_NO_DISPONIBLE


class ErrorConfiguracion(ErrorAsistente):
    """Falta una variable de entorno, tiene un valor inválido o la clave fue rechazada."""

    mensaje_por_defecto = MENSAJE_NO_DISPONIBLE


class ErrorConexion(ErrorAsistente):
    """Sin conexión a internet o tiempo de espera agotado (RNF-12)."""

    mensaje_por_defecto = MENSAJE_SIN_CONEXION


class ErrorCuota(ErrorAsistente):
    """Cuota o créditos de la API agotados (429 / RESOURCE_EXHAUSTED)."""

    mensaje_por_defecto = MENSAJE_CUOTA_GEMINI


class ErrorServicio(ErrorAsistente):
    """El servicio respondió algo inesperado (por ejemplo, un JSON inválido)."""

    mensaje_por_defecto = MENSAJE_RESPUESTA_INVALIDA
