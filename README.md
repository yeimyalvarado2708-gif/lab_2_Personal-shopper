# Asistente con voz "Personal Shopper"

**Laboratorio 2 · Desafío 1 · LE Claude Code** · Autora: Yeimy Alvarado

Asistente de atención al cliente para "Personal Shopper", un emprendimiento de Guápiles que compra por encargo en PriceSmart San José. Responde en texto y en audio las preguntas frecuentes del servicio (tarifas, fechas de compra, entregas y pagos) usando **solo** su base de conocimiento, y además calcula un estimado de la cuenta.

- **Texto:** Google Gemini (`gemini-3.5-flash-lite`), con controles para no inventar datos.
- **Voz:** ElevenLabs (voz prediseñada, modelo `eleven_multilingual_v2`).
- **Interfaz:** Streamlit, con tres pestañas: Preguntar, Estimar e Historial.

Los documentos de ingeniería están en [`intent.md`](intent.md) (problema y objetivos), [`spec.md`](spec.md) (requisitos y diseño) y [`plan.md`](plan.md) (tareas, evidencias e iteraciones).

---

## 1. Requisitos

- **Python 3.11 o superior.** Se desarrolló y probó con Python 3.14.7 en macOS. Para ver su versión: `python3 --version`.
- **Git**, para descargar el proyecto.
- Para usar las API reales (no hacen falta en el modo demo):
  - Una cuenta en [Google AI Studio](https://aistudio.google.com/) para la clave de Gemini.
  - Una cuenta gratuita en [ElevenLabs](https://elevenlabs.io/) para la clave y la voz.

## 2. Instalación

Los comandos son para la Terminal de macOS o Linux. En Windows, las diferencias se indican aparte.

```bash
# 1. Descargar el proyecto y entrar a la carpeta
git clone https://github.com/yeimyalvarado2708-gif/lab_2_Personal-shopper.git
cd lab_2_Personal-shopper

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Instalar las dependencias (versiones exactas)
pip install -r requirements.txt
```

Con el entorno activado, la línea de la Terminal empieza con `(.venv)`. Cada vez que abra una Terminal nueva para usar el proyecto, vuelva a activarlo con `source .venv/bin/activate`.

## 3. Configuración del archivo `.env`

Las claves van en un archivo `.env` que **nunca se sube a Git** (está en `.gitignore`). Créelo a partir de la plantilla:

```bash
cp .env.example .env             # Windows: copy .env.example .env
```

Abra `.env` y complete los valores:

| Variable | ¿Obligatoria? | Valor por defecto | Cómo obtenerla |
|---|---|---|---|
| `GEMINI_API_KEY` | Sí, si `MODO_DEMO=false` | — | Google AI Studio → *Get API key*. |
| `GEMINI_MODEL` | No | `gemini-3.5-flash-lite` | Puede cambiarse por otro modelo Flash disponible, sin tocar el código. |
| `ELEVENLABS_API_KEY` | Sí, si `MODO_DEMO=false` | — | ElevenLabs → *API Keys*. Bastan tres permisos: *Text to Speech* (acceso), *Voices* (lectura) y *User* (acceso). |
| `ELEVENLABS_VOICE_ID` | Sí, si `MODO_DEMO=false` | — | El `voice_id` de una voz **prediseñada (premade)** de su cuenta. En el plan gratuito, las voces de la Biblioteca de voces **no** se pueden usar por API. |
| `ELEVENLABS_MODEL` | No | `eleven_multilingual_v2` | Modelo multilingüe con español. |
| `LIMITE_CARACTERES_RESPUESTA` | No | `400` | Largo máximo de cada respuesta. |
| `TIEMPO_ESPERA_API` | No | `20` | Segundos máximos de espera por cada API. |
| `MODO_DEMO` | No | `false` | `true` para usar la app sin API ni claves (sección 5). |

Para revisar la configuración **sin mostrar las claves** (solo dice si cada una está o falta):

```bash
python -m src.config
```

## 4. Ejecución

```bash
streamlit run app.py
```

Streamlit abre la app en el navegador (normalmente en `http://localhost:8501`). Para detenerla, presione `Ctrl+C` en la Terminal.

- **Preguntar:** escriba una pregunta o use las preguntas rápidas. Cada respuesta muestra su fuente (por ejemplo, "Fuente: FAQ-14") y su categoría, y trae un reproductor de audio que **no** suena solo.
- **Estimar:** calcula el total con el monto de la factura, la zona de entrega y si es la primera compra. Funciona sin internet y no usa ninguna API.
- **Historial:** las consultas de la sesión, de la más nueva a la más antigua. Vive solo en memoria: se borra al recargar la página.

> **Importante (Visual Studio Code):** la Terminal de VS Code puede cargar las variables del `.env` al abrirse, y esas variables tienen prioridad sobre el archivo. Si cambia `MODO_DEMO` (u otra variable) en `.env` y la app no toma el cambio, abra una **Terminal nueva** o indíquela en el mismo comando, por ejemplo `MODO_DEMO=false streamlit run app.py`. Por la misma razón, `python -m src.config` puede decir "configurada" aunque el `.env` esté vacío, si la Terminal ya trae esas variables (pasa con la opción `python.terminal.useEnvFile` de VS Code, incluso después de cambiar de carpeta).

> Si cambia el código o los estilos con la app abierta y no ve el cambio al recargar el navegador, detenga la app con `Ctrl+C` y vuelva a iniciarla.

## 5. Modo demostración (sin créditos o sin conexión)

Si se agotan los créditos, no hay internet o no tiene claves, active el modo demo:

```bash
MODO_DEMO=true streamlit run app.py
```

(o ponga `MODO_DEMO=true` en `.env`). En este modo:

- **No se llama a Gemini ni a ElevenLabs** y no se necesitan claves.
- Las respuestas se buscan por palabras clave en la base y llevan la marca **[RESPUESTA SIMULADA]**.
- La app muestra la etiqueta "DEMO" y la franja *"Modo demostración: las respuestas son simuladas."*
- No hay audio; en su lugar aparece un aviso.
- La calculadora, las fechas y el historial funcionan igual.

## 6. Pruebas

```bash
python -m pytest -q
```

Corre todas las pruebas automatizadas (682 al 2026-11-26). **No llaman a las API reales:** usan *mocks*, y `tests/conftest.py` bloquea la red durante las pruebas, así que no gastan créditos.

La evaluación con la API real es aparte y se corre **una sola vez** (ya se hizo el 2026-11-26; resultados en `evidencias/`):

```bash
python tests/evaluar.py --demo   # ensayo sin API: no gasta nada ni guarda archivos
python tests/evaluar.py          # Gemini real: 33 preguntas (no se repite si ya existe la del día)
```

## 7. Limitaciones conocidas

- **ElevenLabs, plan gratuito:** es solo para uso **personal y no comercial**. Para usar el asistente en el negocio real se necesitaría un plan pago. Además, tiene 10 000 caracteres al mes; para cuidarlos, los audios se guardan en `cache_audio/` y una respuesta repetida no gasta créditos.
- **Gemini, plan gratuito:** tiene límites de uso (para `gemini-3.5-flash-lite`, 15 solicitudes por minuto y 500 por día, verificados el 2026-11-25) y sus propias condiciones de uso de datos. Si se agota la cuota, la app lo avisa y sugiere escribir por WhatsApp.
- **Números ficticios:** el número de SINPE Móvil y el de WhatsApp (8888-0000) son **ficticios**, solo para el laboratorio.
- **Respuestas breves:** cada respuesta tiene **máximo 400 caracteres**. Si una respuesta es más larga, se recorta en la última oración completa.
- **Solo información de la base:** el asistente no conoce precios, marcas ni existencias de productos de PriceSmart. Si no tiene la información, lo dice y ofrece el WhatsApp.
- **Sin cálculos en el chat:** para saber cuánto pagar, el chat remite a la pestaña Estimar. El resultado es un estimado; el total final depende de la factura real.
- **Evaluación:** en la evaluación con Gemini real (T-33), 4 de 5 preguntas fuera de la base recibieron el mensaje esperado. El caso que falló (precio de un producto) se corrigió en el ciclo C-06 y pasó al reevaluarlo, pero los otros 32 casos no se volvieron a evaluar con ese cambio. El detalle está en la sección 7 de [`plan.md`](plan.md).
- **Historial:** solo dura la sesión; no se guarda en disco por privacidad.

## 8. Estructura del proyecto

```
lab_2_Personal-shopper/
├── app.py                    ← interfaz de Streamlit
├── src/
│   ├── config.py             ← lee .env y verifica la configuración
│   ├── base_conocimiento.py  ← carga y valida la base
│   ├── validacion.py         ← valida preguntas y montos
│   ├── calculadora.py        ← estimado de cuenta y próxima fecha de compra
│   ├── gemini_client.py      ← prompt, llamada a Gemini y errores
│   ├── asistente.py          ← flujo completo y controles para no inventar datos
│   ├── voz.py                ← audio con ElevenLabs y caché
│   ├── demo.py               ← respuestas del modo demo
│   ├── historial.py          ← entradas del historial
│   ├── texto.py              ← recorte de respuestas a 400 caracteres
│   ├── errores.py            ← errores propios y mensajes para el cliente
│   └── estilos.py            ← CSS y HTML de la interfaz
├── data/base_conocimiento.json  ← 23 preguntas frecuentes, tarifas, calendario y zonas
├── tests/                    ← pruebas automatizadas, conjunto y script de evaluación
├── evidencias/               ← capturas y resultados de la evaluación (sin claves)
├── docs/prototipo_interfaz.html ← referencia visual de la interfaz
├── .streamlit/config.toml    ← colores del tema (sin secretos)
├── .env.example              ← plantilla de variables, sin claves
└── requirements.txt          ← dependencias con versiones exactas
```

`.env` y `cache_audio/` existen en su computadora pero **no** están en el repositorio.
