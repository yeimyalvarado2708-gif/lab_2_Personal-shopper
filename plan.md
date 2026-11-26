# plan.md — Plan de implementación del Asistente "Personal Shopper"

**Laboratorio 2 · Desafío 1 · LE Claude Code**
**Autora:** Yeimy Alvarado
**Fecha de inicio:** 2026-11-23
**Versión:** 1.31
**Documentos relacionados:** `intent.md` v1.0 · `spec.md` v1.13 · `data/base_conocimiento.json` v1.4 · `tests/preguntas_evaluacion.json` v1.0

---

## 1. Cómo se usa este plan

- Las tareas se hacen **una por una, en orden**. Claude Code implementa **solo la primera tarea pendiente**, explica los archivos que cambió y propone pruebas. Yeimy ejecuta, revisa y valida antes de pasar a la siguiente.
- Una tarea pasa a **Hecho** solo cuando su **evidencia** existe: la prueba pasa, la captura está guardada o el commit está hecho.
- Cada tarea terminada lleva un **commit en Git** con su ID, por ejemplo: `T-08: calculadora con pruebas`.
- Cada error importante se registra como un **ciclo de desarrollo** en la sección 5.
- Para cuidar los créditos, se trabaja con `MODO_DEMO=true` y con mocks hasta la fase 5 (ver la sección 6).

**Responsables:**

| Responsable | Rol |
|---|---|
| **Yeimy** | Decide, redacta los prompts, ejecuta, revisa el código, valida y registra la evidencia. Es la responsable final de cada tarea. |
| **Claude Code** | Propone e implementa el código y las pruebas de cada tarea, siempre con la revisión de Yeimy. |

**Estados:** ⬜ Pendiente · 🔄 En curso · ✅ Hecho · ⛔ Bloqueado

**Prompt base para cada tarea de implementación** (prompt 2 del laboratorio):

> Lee intent.md, spec.md y plan.md. Implementa únicamente la primera tarea pendiente, explica los archivos modificados, propone pruebas y espera validación antes de continuar.

---

## 2. Fases y tareas

### Fase 0 — Definición y diseño (antes de programar)

| ID | Tarea | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|
| T-01 | Redactar `intent.md` (problema, usuarios, objetivos, historias de usuario, éxito). | Yeimy | ✅ Hecho | `intent.md` v1.0 en el repositorio. |
| T-02 | Crear la base de conocimiento con al menos 12 FAQ verificables. | Yeimy | ✅ Hecho | `data/base_conocimiento.json` v1.4: 23 FAQ, todas de máximo 400 caracteres. |
| T-03 | Redactar `spec.md` y hacer la revisión de arquitectura (prompt 1 del laboratorio). | Yeimy | ✅ Hecho | `spec.md` v1.1, con 31 RF y 16 RNF. Iteraciones D-1 a D-4 (sección 5.1). |
| T-04 | Definir el conjunto de evaluación antes de programar. | Yeimy | ✅ Hecho | `tests/preguntas_evaluacion.json` v1.0, con 33 casos. |
| T-05 | Redactar `plan.md`. | Yeimy | ✅ Hecho | Este documento. |

### Fase 1 — Preparación del entorno y lógica local (sin API)

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-06 | Verificar Python 3.11+ en la Mac (`python3 --version`) y crear el entorno virtual `.venv`. | RNF-10 | Yeimy | ✅ Hecho | Python 3.14.7 verificado y `.venv` creado (2026-11-23). Captura `evidencias/T-06_python_venv.png` (commit `44d0cf1`), revisada sin claves visibles. |
| T-07 | Iniciar Git y crear el repositorio en GitHub. Crear `.gitignore` y `.env.example` (sin secretos). | RNF-01, RNF-02 | Yeimy + Claude Code | ✅ Hecho | Commit `211a2e2` subido a GitHub (repositorio público `yeimyalvarado2708-gif/lab_2_Personal-shopper`). `git check-ignore .env` responde `.env`. `.env.example` con las claves vacías. Revisado el 2026-11-23. |
| T-08 | Crear la estructura de carpetas y `requirements.txt`; instalar las dependencias y fijar las versiones. | RNF-10, RNF-16 | Claude Code | ✅ Hecho | Commit `44d0cf1` subido a GitHub. `pip install -r requirements.txt` y `pip check` sin errores; las 5 dependencias con versión exacta; carpetas `src/`, `tests/`, `data/`, `cache_audio/` y `evidencias/` creadas; versiones anotadas en la sección 8 (2026-11-24). |
| T-09 | `src/errores.py` y `src/config.py`: excepciones propias y lectura de `.env` sin mostrar valores. | RF-18, RNF-01, RNF-11 | Claude Code | ✅ Hecho | Commit `afc57c2` (2026-11-24). Con `.env` incompleto, `python -m src.config` dice qué variable falta sin mostrar claves (captura `evidencias/evidencia t9.png`). Se agregaron `tests/test_config.py` (21 pruebas aprobadas) y `pytest.ini`, que no estaban en la sección 10 del spec. |
| T-10 | `src/base_conocimiento.py`: carga y validación del JSON. | RF-03 | Claude Code | ✅ Hecho | Commit `2620025` (2026-11-24). `test_base_conocimiento.py` pasa: 27 pruebas (captura `evidencias/evidencia t10.png`). Total del proyecto: 48 pruebas aprobadas. |
| T-11 | Prueba de coherencia de la base (montos de las FAQ = `tarifas`; respuestas ≤ 400 caracteres). | RNF-14, RF-27 | Claude Code | ✅ Hecho | Commit `8367a6e` (2026-11-24), subido a GitHub. `test_coherencia_base.py` pasa: 79 pruebas (FAQ-02, FAQ-03, FAQ-06, FAQ-07, revisión general de montos y porcentajes, y 400 caracteres en las 23 FAQ). Prueba de detección: con ₡2.500 en FAQ-07 fallan 2 pruebas que nombran a FAQ-07 (captura `evidencias/evidencia t11.png`). Total del proyecto: 127 pruebas aprobadas. |
| T-12 | `src/validacion.py`: validar la pregunta y el monto. | RF-02, RF-16 | Claude Code | ✅ Hecho | Commit `e3658af` (2026-11-24). `test_validacion.py` pasa: 39 pruebas (pregunta vacía, solo espacios, 500/501 caracteres; monto vacío, texto, cero y negativo). `validar_monto()` acepta además el formato de Costa Rica ("₡30.000" = 30000), que no estaba explícito en el spec. Captura `evidencias/evidencia t12.png`. Total del proyecto: 166 pruebas aprobadas. |
| T-13 | `src/calculadora.py`: `calcular_cuenta()` con los 7 casos de referencia y `formatear_colones()`. | RF-13 a RF-15, D-08 | Claude Code | ✅ Hecho | Commit `ba98614` (2026-11-24). `test_calculadora.py` (parte de la cuenta) pasa al 100%: 68 pruebas, con los 7 casos de referencia. Decisiones aprobadas por Yeimy: redondeo al colón con mitades hacia arriba; monto llevado a céntimos para que no haya huecos entre rangos; con cortesía se informa el porcentaje del rango con cargo ₡0; la zona no registrada se rechaza con "Zona no registrada. Será valorada y pronto le enviaremos más detalles.", también en la primera compra; formato `₡36.500` / `₡30.000,50`. Captura `evidencias/evidencia t13.png`. Total del proyecto: 234 pruebas aprobadas. |
| T-14 | `src/calculadora.py`: `proxima_fecha_compra()` y `hoy_costa_rica()` (zona horaria y máximo de 8 semanas). | RF-12, RF-28, RF-29 | Claude Code | ✅ Hecho | Commit `fc6e38a` (2026-11-24), subido a GitHub. Pasan los 5 casos de fechas de 5.4 y el caso de zona horaria (05:30 UTC del jueves = miércoles 11:30 p. m. en Costa Rica). `test_calculadora.py`: 86 pruebas (68 de T-13 + 18 de T-14). Decisiones: sin fecha en 8 semanas → ambas fechas `None` y se muestra el texto fijo de RF-29; `dia_compra` y `dia_limite_lista` se leen del JSON (RNF-08); no se revisa si la fecha límite está cancelada; en Windows haría falta `tzdata`. Captura `evidencias/evidencia t14.png`. Total del proyecto: 252 pruebas aprobadas. |
| T-15 | `src/demo.py`: respuestas simuladas por palabras clave, sin distinguir mayúsculas ni tildes. | RF-20, RF-30 | Claude Code | ✅ Hecho | Commit `2a161b4` (2026-11-24), subido a GitHub. `test_demo.py` pasa: 30 pruebas (sin red ni SDK de las API; sin distinguir mayúsculas, tildes ni plural; sin coincidencia → mensaje fijo de RF-21 con `informacion_suficiente: false`). "¿Cuándo es la próxima compra?" usa las fechas calculadas con fuente CALENDARIO. Categoría sin coincidencia: "Sin información". Observación: con las 20 preguntas `dentro_base` del conjunto de evaluación, el modo demo acierta 14/20 (no afecta la evaluación oficial con Gemini, T-33). Captura `evidencias/evidencia t15.png`. Total del proyecto: 282 pruebas aprobadas. |

### Fase 2 — Integración con Gemini

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-16 | Obtener la clave en Google AI Studio, confirmar que `gemini-3.5-flash-lite` está disponible y anotar los límites gratuitos vigentes. | Pendiente del spec | Yeimy | ✅ Hecho | 2026-11-25: clave en `.env` (no aparece en capturas; `.env` ignorado por Git); modelo `gemini-3.5-flash-lite` confirmado consultando los datos del modelo, sin generar texto (entrada 1 048 576 tokens, salida 65 536) — captura `evidencias/evidencia t16.png`. Ciclo C-01 registrado. Límites gratuitos anotados en la sección 8 (captura `evidencias/evidencia t16 limites.png`; AI Studio no permite capturar los títulos de las columnas, y Yeimy confirma que las cifras son RPM, TPM y RPD). |
| T-17 | `src/gemini_client.py`: prompt con delimitadores, respuesta en JSON, temperatura 0.2 y tiempo de espera. | RF-04, RF-05, RF-22, RF-23, RNF-12, RNF-13 | Claude Code | ✅ Hecho | Commit `6a616a7` (2026-11-25). `test_gemini_client.py` pasa: 20 pruebas con mocks, sin red (respuesta exitosa; modelo, temperatura 0.2 y JSON; pregunta entre delimitadores que no se pueden cerrar desde la pregunta; base en las instrucciones; fechas y caso sin fecha; sin clave no se crea el cliente; tiempo de espera; la clave nunca viaja en el prompt). Se revisó el prompt generado con sus 10 reglas. Captura `evidencias/evidencia t17.png`. Decisiones aprobadas por Yeimy: sin reintentos automáticos del SDK (el reintento por JSON inválido va en T-18); categoría limitada a las 6 de la base o "Sin información"; tono de "usted" en español de Costa Rica; base completa con palabras clave y metadatos; fecha límite "durante todo el día" (D-11). Los errores del SDK y el JSON inválido se traducen en T-18. Total del proyecto: 302 pruebas aprobadas. |
| T-18 | Traducir los errores de Gemini (falta de clave, clave inválida, red, cuota, JSON inválido) a las excepciones propias. | RF-18, sección 7 | Claude Code | ✅ Hecho | Commit `f0745c7` (2026-11-25). Prueba manual de falta de clave (`cargar_config(entorno={})`): el cliente ve *"En este momento el asistente no está disponible. Escríbanos por WhatsApp al 8888-0000 y con gusto le ayudamos."* y la consola muestra solo *"Falta GEMINI_API_KEY en .env"*, sin valores de claves. Captura `evidencias/evidencia t18.png`. `test_gemini_client.py` pasa: 51 pruebas (20 de T-17 + 31 de T-18) con mocks, sin red: clave inválida (400 `API_KEY_INVALID`, 401, 403) y modelo inexistente (404) → `ErrorConfiguracion`; sin conexión o tiempo agotado → `ErrorConexion`; 429 o `RESOURCE_EXHAUSTED` → `ErrorCuota`; 500/503 → `ErrorServicio`; JSON inválido (7 variantes) → un reintento y luego `ErrorServicio`. En todos los casos se verifica el mensaje al cliente de la sección 7 y que ni el mensaje ni la consola muestren la clave; la consola tampoco registra la pregunta (RNF-15). Reintentos automáticos del SDK fijados en 1 intento (`INTENTOS_HTTP = 1`) y verificados contando las solicitudes HTTP reales (exactamente una ante 429, 500, 503, 504 y fallos de red), con una prueba de control que sí detecta 3 intentos. Captura `evidencias/evidencia t18 reintentos.png` (7 pruebas de solicitud única y de control, aprobadas). Decisión de Yeimy: los errores 500/503 muestran un mensaje nuevo ("Intente de nuevo en unos minutos o escríbanos por WhatsApp…"), sin reintento; se agregó con el 404 a la sección 7 del spec (v1.2). Total del proyecto: 333 pruebas aprobadas. |
| T-19 | `src/asistente.py`: controles anti-invención (fuentes, mensaje fijo, verificación de montos, dos partes, recorte a 400). | RF-06, RF-07, RF-10, RF-21, RF-24, RF-25 | Claude Code | ✅ Hecho | Commit `ebc91ab` (2026-11-25). Prueba manual con `MODO_DEMO=true` (sin API): "¿A qué número hago el SINPE?" → SINPE 8888-0000, fuente FAQ-14, sin controles; "¿Cuánto pago por ₡30.000 con entrega en La Trocha?" → control RF-24 bloquea los montos ₡4.500, ₡30.000, ₡34.500 y ₡36.500 y muestra el mensaje fijo de la calculadora (fuente FAQ-03); "¿Venden ropa?" → control RF-21, mensaje fijo con WhatsApp. Captura `evidencias/evidencia t19.png`. `test_asistente.py` pasa: 46 pruebas con mocks, sin red (fuentes RF-07; mensaje fijo RF-21 con el WhatsApp de la base; montos en cualquier formato y porcentajes RF-24; teléfonos y fechas no cuentan como montos; EV-29 a EV-31; dos partes RF-25; recorte RF-10 en oración completa, nunca dentro de un monto, o en palabra + "…"; prefijo de modo demo; `responder()` completo; la consola no registra la pregunta). Las 33 preguntas de evaluación pasaron por `responder()` en modo demo: sin rechazos de respuestas correctas y respuesta más larga de 379 caracteres. Decisiones aprobadas por Yeimy: RF-24 más estricto (si la pregunta trae un monto, solo se permiten ₡2.000, ₡15.000 y ₡40.000, porque el ejemplo de FAQ-03 coincide con EV-29); porcentajes verificados (solo 20%, 15% y 10%); recorte en la última palabra + "…" si no hay fin de oración; `responder()` incluido en T-19 (el audio va en T-23). El texto de WhatsApp y el prefijo `[RESPUESTA SIMULADA]` cuentan dentro del límite; si RF-24 reemplaza el texto se conservan las fuentes válidas; el resultado agrega `recortado` y `controles`. Precisiones agregadas a RF-24 y RF-10 (`spec.md` v1.3). Total del proyecto: 379 pruebas aprobadas. **Ajuste posterior (ciclo C-03, commit `dfa9ad9`):** el mensaje fijo de RF-24 explica la fórmula con el menor y el mayor porcentaje y el costo de entrega tomados de `tarifas` (`asistente.mensaje_calculadora()`, 205 caracteres); `test_asistente.py` pasa a 54 pruebas y el total del proyecto a 387 (`spec.md` v1.4). |
| T-20 | **Primera prueba real de Gemini:** una pregunta desde la consola, con `MODO_DEMO=false`. | Prueba manual 1 | Yeimy | ✅ Hecho | 2026-11-25: primera llamada real a Gemini con `MODO_DEMO=false` y modelo `gemini-3.5-flash-lite`. "¿A qué número hago el SINPE?" → *"Puede hacer el SINPE Móvil al número 8888-0000 (número ficticio para el laboratorio)."* · fuente FAQ-14 · categoría Pagos · sin controles activados (respuesta correcta según la base). Captura `evidencias/evidencia t20.png`, sin claves visibles. Es la evidencia de respaldo de la integración real con Gemini (plan alternativo de R-02). |

### Fase 3 — Integración con ElevenLabs

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-21 | Obtener la clave de ElevenLabs, elegir una voz **prediseñada (premade)** y anotar su `voice_id` en `.env`. Revisar los créditos del mes. | Pendiente del spec | Yeimy | ✅ Hecho | 2026-11-25: clave de ElevenLabs creada con solo 3 permisos (De texto a voz: Acceso; Voces: Leído; Usuario: Acceso) y guardada en `.env`. Créditos: plan Free, 10 000 de 10 000 disponibles, se renuevan el 2026-12-26 (sección 8). Voz elegida por Yeimy: **Bella - Professional, Bright, Warm** (`premade`, `voice_id` `hpp4J3VqNfWAUOO0d1Us`), confirmada por API (`voices.get`: categoría `premade`; `faltantes_elevenlabs()` vacío). Primera elección descartada: "Luisa - Amigable, Versátil", de la Biblioteca de voces; la API respondió `voice_not_found` porque no está en la cuenta y, en el plan gratuito, las voces de la Biblioteca no se pueden usar por API (spec, `ELEVENLABS_VOICE_ID`). Las consultas de voces y créditos no gastan créditos. Capturas `evidencias/evidencia t21.png` y `evidencias/evidencia t21 b.png` (créditos y lista de voces prediseñadas, sin claves visibles). |
| T-22 | `voz.normalizar_para_audio()`: montos, teléfonos y símbolos. | RF-26 | Claude Code | ✅ Hecho | Commit `03eba8a` (2026-11-25). Los 4 casos de 5.6.1 del spec pasan. `test_voz.py`: 62 pruebas, sin llamadas a ElevenLabs (casos del spec; montos en varios formatos, sin separador de miles y sin repetir "colones"; céntimos; teléfonos de 8 dígitos con guion, espacio o juntos; montos de 8 cifras que no se leen como teléfono; `%`, `+` y `=`; símbolos `*`, `#`, `_`, `` ` `` y `~`; textos reales de FAQ-03, la calculadora y el mensaje sin información; las 23 respuestas de la base sin símbolos para la voz; el texto en pantalla no cambia). Prueba manual: `factura de ₡30.000 + 15% = ₡34.500` → *"factura de 30000 colones más 15 por ciento es igual a 34500 colones"*. Captura `evidencias/evidencia t22.png`. Decisiones de Yeimy: `%`, `+` y `=` se leen en palabras ("por ciento", "más", "es igual a"); los céntimos se dejan con coma ("₡14.999,99" → "14999,99 colones"). Agregadas a RF-26 y 5.6.1 (`spec.md` v1.5). La pronunciación real con la voz Bella se comprueba en T-24. Total del proyecto: 449 pruebas aprobadas. |
| T-23 | `src/voz.py`: llamada a ElevenLabs, caché en `cache_audio/`, tiempo de espera y traducción de errores. | RF-09, RF-11, RF-19, RNF-12 | Claude Code | ✅ Hecho | Commit `b7a9dd1` (2026-11-25). `voz.sintetizar()`: recorta, prepara el texto (T-22), busca en `cache_audio/` (SHA-256 de texto + voz + modelo) y, si no está, llama a ElevenLabs y guarda el MP3. La caché funciona aunque falte la clave o no haya conexión (sección 9). Errores traducidos a la sección 7: créditos agotados → `ErrorCuota`; clave inválida o sin permiso, voz inexistente o de plan pago y modelo inexistente → `ErrorConfiguracion` ("solo en texto"); 429 y 5xx → `ErrorServicio`; sin red o tiempo agotado → `ErrorConexion`. `asistente.responder()` entrega además `audio`, `audio_desde_cache` y `aviso_audio`: un fallo de audio nunca impide el texto (RF-19) y el modo demo no genera audio (RF-20). `recortar()` pasa a `src/texto.py`; `tests/conftest.py` bloquea la red real en todas las pruebas. 47 pruebas nuevas con mocks y un servidor HTTP falso, sin gastar créditos (40 en `test_voz.py`, que llega a 102; 7 en `test_asistente.py`), incluida la cuenta de solicitudes: exactamente 1 ante 429, 500, 502, 503 y 504. Prueba manual en modo demo: `audio: None | aviso: Modo demostración: el audio no está disponible.` Captura `evidencias/evidencia t23.png`. Decisiones de Yeimy: sin reintentos del SDK (`max_retries=0`; en la versión 2.79.0 `convert()` ya no reintenta, se fija igual por si el SDK cambia); MP3 estándar `mp3_44100_128`; audio conectado con `responder()` en esta tarea; texto de más de 400 caracteres recortado con la regla de RF-10; aviso del modo demo *"Modo demostración: el audio no está disponible."* Agregadas a RF-20, 5.6 y la sección 7 (`spec.md` v1.6). Total del proyecto: 496 pruebas aprobadas. |
| T-24 | **Primera prueba real de audio:** generar un audio con monto y teléfono, y escucharlo. | Pruebas manuales 2 y 6 | Yeimy | ✅ Hecho | 2026-11-25: primer audio real con ElevenLabs (voz Bella, `eleven_multilingual_v2`, `mp3_44100_128`) generado con `voz.sintetizar()`. Texto en pantalla: *"La entrega en La Trocha cuesta ₡2.000 y el servicio es del 15%. Puede hacer el SINPE Móvil al 8888-0000."* → texto para la voz: *"…cuesta 2000 colones y el servicio es del 15 por ciento. Puede hacer el SINPE Móvil al 8 8 8 8, 0 0 0 0."* Resultado: audio de 10 s (160 KB), `desde_cache: False`, guardado también en `cache_audio/`. **Nota de Yeimy:** "todo se escucha muy bien, claro y bien pronunciado" (monto, porcentaje y teléfono). Créditos: 102 usados, quedan 9 898 de 10 000 (el contador de ElevenLabs tardó en actualizarse: el comando mostró 10000 → 10000 y la consulta posterior confirmó los 102). Archivos `evidencias/evidencia t24.mp3` y `evidencias/evidencia t24.png` (sin claves visibles). Cubre las pruebas manuales 6 y, en parte, 2 (la reproducción en la interfaz se verifica en T-26). |

### Fase 4 — Interfaz (Streamlit)

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-25 | `app.py`: chat con campo de pregunta, botón Enviar (desactivado mientras procesa), respuesta, fuente y categoría. | RF-01, RF-08, RF-31 | Claude Code | ✅ Hecho | Commit `0bf9b75` (2026-11-25). La app abre con `MODO_DEMO=true streamlit run app.py` y responde en modo demo: encabezado, tarjeta de próxima compra con "¡Cierra hoy!" (D-14), pestañas Preguntar, Estimar e Historial (las dos últimas con "Disponible pronto." hasta T-27 y T-28), preguntas rápidas, burbujas con "Fuente: FAQ-14" y la categoría "Pagos", y pie con WhatsApp. Captura `evidencias/evidencia t25.png`. Archivos: `app.py`, `src/estilos.py` (CSS y HTML con `html.escape`, D-17) y `.streamlit/config.toml` (colores, sin secretos); `.streamlit/secrets.toml` agregado a `.gitignore`. 26 pruebas nuevas: `test_estilos.py` (13) y `test_app.py` (13, con `AppTest` en modo demo: pregunta escrita y rápidas, solo la última conversación, pregunta vacía, texto con código escapado, controles desactivados mientras procesa (RF-31), errores amigables, base dañada y la consola sin la pregunta). Decisiones de Yeimy: trato de "usted" en toda la app, también en el saludo (*"¿Necesita información de nuestro servicio?"*); T-25 incluye la estructura completa y la pestaña Preguntar; solo se ve la última conversación. Hallazgo: el selector `button[data-baseweb="tab"]` ya no existe en Streamlit 1.67; las pestañas son `[data-testid="stTab"]` (`spec.md` v1.8). **Nota:** los cambios de diseño de `spec.md` v1.7 (D-12 a D-18), escritos por Yeimy, entraron sin querer en el commit `b7a9dd1` de T-23; el contenido es correcto y no se reescribió el historial. Total del proyecto: 522 pruebas aprobadas. **Ajuste aprobado por Yeimy (commit `5999df8`):** tres diferencias con el prototipo vistas en la captura: (1) la respuesta no tenía fondo celeste porque la página y la burbuja eran del mismo color → página celeste y la app en una tarjeta blanca; (2) el botón Enviar salía blanco porque los formularios no reciben la clase `st-key-…` → el botón tiene su propia `key` (`enviar`) y es fucsia; (3) raya roja bajo la pestaña activa → se ocultó `.react-aria-SelectionIndicator` y la línea gris de la lista. Los estilos se verificaron en Chrome sin ventana (computados: Enviar `rgb(216, 27, 106)`, burbuja `rgb(234, 244, 253)`). En la primera revisión de Yeimy se seguía viendo el CSS anterior: al recargar el navegador Streamlit no volvió a cargar `src/estilos.py`; se resolvió reiniciando la app. Captura `evidencias/evidencia t25 ajuste.png`. |
| T-26 | Reproductor de audio (sin reproducción automática) y avisos cuando el audio no está disponible. | RF-09, RF-19, D-03 | Claude Code | ✅ Hecho | Commit `41b0a99` (2026-11-25). Reproductor nativo `st.audio` con `autoplay=False` debajo de la respuesta; aviso 🔇 en su lugar cuando no hay audio (RF-19) o en modo demo (D-18); botón verde "Escribir por WhatsApp" cuando no hay información (D-15) y en respuestas con dos partes (RF-25). Prueba real con `MODO_DEMO=false`: "¿A qué número hago el SINPE?" y "¿Cuánto cobran?" (FAQ-02, Tarifas) con reproductor de 0:16 que no suena solo y se oye bien (captura `evidencias/evidencia t26.png`). Decisiones de Yeimy: reproductor nativo (D-17); sin información no se genera audio (ahorra créditos); WhatsApp abre el chat con *"Hola, tengo una consulta sobre el servicio de Personal Shopper."* (sin la pregunta); dos partes llevan audio y botón (`spec.md` v1.9). 13 pruebas nuevas (`test_app.py`, `test_estilos.py`, `test_asistente.py`). Corrección: los íconos de Streamlit tomaban la letra Baloo 2 y el botón mostraba la palabra "chat". **Durante la prueba:** (1) la pronunciación de "₡40.000" falló y se corrigió en el ciclo C-04; (2) una pregunta recibió un error 5xx real de Gemini y la app mostró el mensaje de la sección 7, sin reintento y sin gastar créditos de audio (manejo de errores de T-18 verificado en vivo); (3) la terminal de VS Code carga las variables del `.env` al abrirse y tienen prioridad sobre el `.env` (`override=False`): al cambiar `MODO_DEMO` hay que abrir una terminal nueva o usar el prefijo `MODO_DEMO=false`; se anotará en el README. Observación corregida en T-27: el "La carga" que se vio en pantalla no lo escribió Gemini sino la traducción automática de Chrome; la clave del audio en caché coincide con el texto "El cargo…" de FAQ-02. Créditos de ElevenLabs: quedan 9 455. Total del proyecto: 565 pruebas aprobadas. |
| T-27 | Formulario de la calculadora de estimado, con su desglose y leyenda. | RF-13 a RF-16 | Claude Code | ✅ Hecho | Commit `c247178` (2026-11-25). Pestaña Estimar: tres tarjetas de rango armadas con `tarifas` (la del rango aplicado, resaltada en su color), monto, una sola lista de zonas con "(+₡2.000)" en las zonas con cargo, casilla de primera compra, desglose (productos, servicio con su porcentaje, entrega y total) con la leyenda de RF-15 y aviso de cortesía; montos inválidos muestran *"Ingrese un monto válido mayor a cero."* sin calcular (RF-16). No llama a ninguna API. Decisiones de Yeimy: monto en campo de texto ("30000", "30.000" o "₡30.000"); formulario vacío al abrir; el monto se recalcula al presionar Enter o salir del campo (`spec.md` v1.11, D-16). 30 pruebas nuevas, incluidos los 7 casos de referencia de la sección 5.3 y el caso ₡30.000 en La Trocha = ₡36.500 (AppTest). Captura `evidencias/evidencia t27.png` (₡30.000, Buenos Aires, primera compra: total ₡30.000 con cortesía). **Nota:** en la captura, la traducción automática de Chrome alteró textos ("carga" por "cargo", "envía" por "envío", montos sin ₡); se guardó igual por decisión de Yeimy. **Ajuste aprobado por Yeimy (commit `2a47e2c`):** Streamlit marca la página como `lang="en"` y Chrome la "traducía" al español; un script mínimo (`estilos.SCRIPT_IDIOMA`) la marca como `lang="es"`, con `translate="no"` y `<meta name="google" content="notranslate">`, sin tocar textos (excepción de D-17, `spec.md` v1.12); se ocultó su contenedor, que dejaba una franja sobre el encabezado. Verificado en Chrome sin ventana. 3 pruebas nuevas. Total del proyecto: 598 pruebas aprobadas. |
| T-28 | Historial de la sesión (mínimo 5, del más reciente al más antiguo, solo en memoria). | RF-17, RNF-15 | Claude Code | ✅ Hecho | Commit `fabdada` (2026-11-25). Pestaña Historial con contador ("Historial (N)", D-13): todas las consultas de la sesión, de la más nueva a la más vieja, cada una con hora, categoría y fuente, pregunta, respuesta y estado del audio; los errores del servicio quedan como "Sin respuesta" (sección 7). Vive solo en `st.session_state` (RNF-15): se borra al recargar y no escribe nada en disco. Nuevo `src/historial.py`. Prueba manual en modo demo con 6 consultas (captura `evidencias/evidencia t28.png`). Decisiones de Yeimy: se muestran todas las consultas; estado del audio y reproductor (desde la memoria, sin gastar créditos); hora en 12 horas de Costa Rica ("11:49 p. m."); las preguntas inválidas no se guardan (`spec.md` v1.13, RF-17). **Error encontrado por Yeimy:** el historial no bajaba y solo se veían 4 consultas; causa: el `overflow: hidden` del ajuste de T-25 recortaba la tarjeta, que Streamlit encogía al alto de la ventana; se corrigió con `flex-shrink: 0` y `height: auto` (verificado en Chrome con una ventana de 800 px) y una prueba que lo vigila. 20 pruebas nuevas, incluida la prueba de aceptación de RF-17 (6 consultas). Total del proyecto: 618 pruebas aprobadas. |
| T-29 | Banner del modo demo y mensajes de error amigables en pantalla. | RF-18, RF-20, sección 7 | Claude Code | ⬜ | Captura con `MODO_DEMO=true`. |

### Fase 5 — Pruebas y verificación

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-30 | `test_seguridad.py` y verificación de que `.env` no está en Git (`git ls-files`). | RNF-01, RNF-02 | Claude Code + Yeimy | ⬜ | Prueba aprobada y captura de `git ls-files`. |
| T-31 | Ejecutar todas las pruebas automatizadas con `pytest`. | Sección 10 del spec | Yeimy | ⬜ | Captura de `pytest` con todas las pruebas aprobadas. |
| T-32 | Pruebas manuales de error: quitar la clave, desconectar internet y simular la cuota agotada. | RF-18, RF-19, prueba manual 4 | Yeimy | ⬜ | Capturas de los tres mensajes amigables. |
| T-33 | `tests/evaluar.py`: recorrer el conjunto de evaluación con la API real (solo Gemini, una vez). | Sección 10 del spec | Claude Code + Yeimy | ⬜ | Resultados en `evidencias/evaluacion_AAAA-MM-DD.json` y revisión humana de cada caso. |
| T-34 | Revisión final (prompt 3 del laboratorio): seguridad, errores, uso de API y criterios de aceptación. Actualizar este plan sin ocultar problemas. | Sección 11 del spec | Yeimy + Claude Code | ⬜ | Sección 7 de este plan completa, con lo que pasó y lo que no. |

### Fase 6 — Entrega

| ID | Tarea | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|
| T-35 | `README.md`: instalación, configuración de `.env`, ejecución, modo demo y limitaciones (sección 13 del spec). | Claude Code + Yeimy | ⬜ | README revisado: alguien puede instalar la app siguiéndolo paso a paso. |
| T-36 | Video o capturas que muestren el texto generado, el audio y el manejo de un error. | Yeimy | ⬜ | Archivo de video o capturas en `evidencias/`, sin claves visibles. |
| T-37 | Completar el registro de iteraciones (mínimo 3 ciclos de código). | Yeimy | ⬜ | Sección 5.2 con al menos C-01 a C-03 completos. |
| T-38 | Reflexión de 250 a 400 palabras: decisiones humanas, limitaciones del modelo, seguridad y aprendizajes. | Yeimy | ⬜ | Archivo `reflexion.md`, con el conteo de palabras. |
| T-39 | Revisar la coherencia final de intent, spec y plan con la app terminada. Subir a GitHub o crear el ZIP. | Yeimy | ⬜ | Enlace del repositorio o ZIP entregado. |

---

## 3. Dependencias entre tareas

| Tarea | Depende de | Motivo |
|---|---|---|
| T-08 a T-15 | T-06, T-07 | Se necesita Python, el entorno virtual y Git. |
| T-11, T-13, T-14, T-15 | T-10 | Usan la base de conocimiento ya cargada. |
| T-17 a T-19 | T-09, T-10, T-14 | Necesitan la configuración, la base y las fechas calculadas. |
| T-20 | T-16, T-17, T-19 | Primera llamada real a Gemini. |
| T-23 | T-09, T-21, T-22 | Necesita la configuración, la voz elegida y la normalización. |
| T-24 | T-23 | Primera llamada real a ElevenLabs. |
| T-25 a T-29 | T-15, T-19, T-23 | La interfaz une todos los módulos. |
| T-33 | T-20, T-25 | La evaluación necesita el flujo completo funcionando. |
| T-35 a T-39 | T-31 a T-34 | La entrega se prepara cuando todo está verificado. |

**Dependencias externas:** cuenta en Google AI Studio, cuenta gratuita en ElevenLabs, cuenta en GitHub, Visual Studio Code con Claude Code y conexión a internet (solo en las fases 2, 3 y 5).

---

## 4. Ruta crítica y prioridades

Si el tiempo se acorta, este es el orden de prioridad:

1. **Mínimos del laboratorio:** T-06 a T-14, T-16 a T-20, T-21 a T-29 (sin el banner ni la calculadora completa), T-30 a T-32 y T-35 a T-39.
2. **Calidad que suma puntos:** T-19 completo (controles anti-invención) y T-33 (evaluación).
3. **Reto adicional:** la fuente y la categoría en pantalla (parte de T-25), y la derivación a WhatsApp (ya incluida en T-19).

---

## 5. Registro de iteraciones

Formato de cada ciclo: **prompt → código/documento → ejecución/revisión → error u observación → corrección → resultado.**

### 5.1 Iteraciones de diseño (ya realizadas)

Estas iteraciones ocurrieron mientras se escribían los documentos de ingeniería, antes de programar.

| Ciclo | Prompt o acción | Resultado inicial | Error u observación | Corrección aplicada | Resultado |
|---|---|---|---|---|---|
| **D-1** | Definir las tarifas y la cortesía de la primera compra en el spec. | El caso "primera compra en Buenos Aires" daba ₡32.000: la cortesía solo eliminaba el cargo del servicio. | La regla real del negocio también regala la entrega en la primera compra. | Se corrigieron RF-14 y la tabla de casos (₡30.000) en el spec, y FAQ-03 y FAQ-04 en la base. | La regla de cortesía coincide con la práctica del negocio. |
| **D-2** | Revisar los mensajes de error del spec. | El mensaje de base de conocimiento ausente decía "Revise el archivo de datos", y otros mencionaban `.env`. | Son mensajes técnicos: el cliente no los entiende ni puede resolver el problema. | Mensajes sencillos con salida a WhatsApp; el detalle técnico pasa a la consola. Se escribió una regla general en la sección 7 del spec. | Todos los mensajes al cliente están escritos para él. |
| **D-3** | Prompt 1 del laboratorio: *"Actúa como arquitecto de software. Lee intent.md y revisa spec.md… señala supuestos y riesgos."* | El spec v1.0 cubría los mínimos. | La revisión encontró 13 huecos: Gemini podía "suavizar" un "no sé" con datos inventados, calcular montos en el chat o ceder ante manipulación, y la base podía desincronizarse, entre otros. | Se agregaron RF-21 a RF-31, RNF-12 a RNF-16, las decisiones D-09 a D-11 y el conjunto de evaluación. | `spec.md` v1.1. |
| **D-4** | Aplicar el límite de 400 caracteres a todas las respuestas. | Se acortó FAQ-06 para que cupiera en el límite. | Al acortarla se perdió la frase para los barrios que no están en la lista; el asistente no habría sabido qué contestar. Se detectó al escribir el conjunto de evaluación. | Se restauró la frase (358 caracteres). | Base de conocimiento v1.4. |

### 5.2 Ciclos de desarrollo de código (se completan durante la implementación)

El laboratorio pide al menos tres. Se registran aquí con datos reales a medida que ocurran. **No se llenan con resultados supuestos.**

| Ciclo | Tarea | Prompt usado | Código generado | Ejecución | Error u observación | Corrección | Resultado |
|---|---|---|---|---|---|---|---|
| **C-01** | T-16 | Comando de verificación del modelo: `m = genai.Client(api_key=...).models.get(model=c.gemini_model)` (cliente creado y usado en una sola línea). | Comando de una línea en la Terminal. | 2026-11-25: falla con `RuntimeError: Cannot send a request, as the client has been closed.` (captura `evidencias/evidencia t16 error C-01.png`). | El cliente de Gemini no se guardó en una variable: Python lo cerró antes de enviar la consulta. No era un problema de la clave ni del modelo. | Guardar el cliente en una variable (`client = genai.Client(...)`) y luego llamar `client.models.get(...)`. **Regla para T-17:** en `gemini_client.py`, el cliente se crea una vez y se guarda; no se encadena en una sola línea. | Responde `models/gemini-3.5-flash-lite` · entrada 1 048 576 · salida 65 536. Modelo confirmado (captura `evidencias/evidencia t16.png`). |
| **C-02** | T-18 | *"confirme si gemini_client.py desactiva o limita esos reintentos, y que una prueba lo verifique."* (prompt a Claude Code después de la revisión del cambio en `spec.md` durante T-18; "esos reintentos" se refiere a los reintentos internos del SDK). | `gemini_client.py` con los reintentos automáticos del SDK fijados en 1 intento (`INTENTOS_HTTP = 1`); pruebas que cuentan las solicitudes HTTP reales y una prueba de control. | 2026-11-25: el error del ciclo C-01 mostraba que el SDK reintenta por su cuenta (líneas `tenacity` y `retry` en la traza). | Riesgo oculto: con reintentos internos, la espera ante una falla podía pasar de los 20 segundos del RNF-12 y gastar cuota, y no se cumpliría la decisión de Yeimy de no reintentar ante 500/503. No se nota cuando todo funciona. | Fijar el SDK en un solo intento y comprobarlo con mocks: exactamente una solicitud ante 429, 500, 503, 504 y fallos de red; la prueba de control confirma que el contador sí detecta 3 intentos. | 7 pruebas aprobadas en 0.44 s, sin red (captura `evidencias/evidencia t18 reintentos.png`). Commit `f0745c7`. Se cumplen el RNF-12 y la decisión de "sin reintento". |
| **C-03** | T-19 | *"Cambia el mensaje fijo de RF-24 por este texto: "El total es su factura más un cargo de servicio del 10% al 20% según el monto, y ₡2.000 si la entrega es en una zona con cargo. Para calcular su cuenta, use la calculadora de estimado en esta misma página.". Agrega una prueba que verifique que el mensaje no pasa de 400 caracteres y que el control de montos no lo bloquea. Actualiza RF-24 en spec.md. "Los porcentajes y el monto de entrega deben tomarse de tarifas en la base de conocimiento, no escribirse fijos en el código.""* | `asistente.mensaje_calculadora()` arma el texto con `tarifas` (menor y mayor porcentaje de `rangos_servicio` y `entrega_domicilio_con_cargo`); pruebas nuevas en `test_asistente.py`: texto aprobado, máximo 400 caracteres (también con el prefijo del modo demo), el control de montos no lo bloquea y el texto sale de `tarifas`, no del código. RF-24 actualizado en `spec.md`. | 2026-11-25: prueba manual en modo demo, "¿Cuánto pago por ₡30.000 con entrega en La Trocha?" (captura `evidencias/evidencia t19.png`). | El control RF-24 bloqueaba toda la respuesta y el cliente recibía solo "use la calculadora", sin la explicación que piden RF-23 y el criterio de EV-29. Pasaba siempre en modo demo, porque FAQ-03 trae un ejemplo con montos. Yeimy descartó un primer mensaje de 375 caracteres por ser muy largo. | Mensaje fijo nuevo y breve (205 caracteres), que explica el cálculo solo con valores permitidos (10%, 20% y ₡2.000) y se arma con los datos de la base para no desactualizarse (RNF-08, RNF-14). | 2026-11-25: `test_asistente.py` pasa: **54 pruebas** en 0.19 s, sin red (46 de T-19 + 8 casos nuevos: texto aprobado; máximo 400 caracteres, con y sin el prefijo del modo demo; 4 preguntas con montos donde el control no bloquea el mensaje; texto armado desde `tarifas`). Captura `evidencias/evidencia c03 pruebas.png`. Commit `dfa9ad9`. Total del proyecto: 387 pruebas aprobadas. |
| **C-04** | T-26 | *"Recargué la página y probé este pero no lee bien. Dice $4000 en 40000. Y dice mince mil colones en vez de 15.000 colones."* (Yeimy, al escuchar en la app con `MODO_DEMO=false` el audio de "¿Cuánto cobran?"). | `voz.normalizar_para_audio()` de T-22 (montos sin separador de miles: "₡40.000" → "40000 colones"), llamado desde `voz.sintetizar()`. | 2026-11-25: respuesta de Gemini con FAQ-02 (*"…menor a ₡15.000; 15% si está entre ₡15.000 y ₡40.000; 10% si es mayor a ₡40.000."*); Bella recibió *"…menor a 15000 colones; … entre 15000 colones y 40000 colones…"*. En T-24 "2000 colones" se había oído bien. | Con cifras de 5 dígitos seguidos, la voz multilingüe se equivoca: leyó "40000" como "4000" y pronunció mal "quince mil". El texto preparado era correcto; el problema era dejarle a la voz la interpretación de los dígitos. Prueba que una revisión con números cortos (T-24) no bastaba. | Decisión de Yeimy: los **montos enteros se dicen en palabras** ("₡40.000" → "cuarenta mil colones"; "₡36.500" → "treinta y seis mil quinientos colones"). Conversor propio en `voz.py` (`numero_en_palabras()`, `monto_en_palabras()`), sin librerías nuevas, de 0 a 999 999 999, con "un colón", "veintiún mil" y "un millón de colones". Los porcentajes siguen como "20 por ciento" y los montos con céntimos como en T-22 ("14999,99 colones"), por decisión de Yeimy. RF-26 y la tabla 5.6.1 actualizados (`spec.md` v1.10). | `test_voz.py`: 27 casos del conversor, el caso de C-04 ("₡15.000 y ₡40.000" → "quince mil colones y cuarenta mil colones") y una prueba de que ningún monto entero de la base llega a la voz como dígitos; total del proyecto: 565 pruebas aprobadas. 2026-11-25: Yeimy escuchó el audio nuevo de "¿Cuánto cobran?" en la app: *"se escucha bien"*. Audio nuevo en `cache_audio/` (23:01, distinta clave que el de 22:47 con el mismo texto en pantalla, lo que confirma el texto en palabras). Captura `evidencias/evidencia t26.png`. Commit `94bf382`. |

**Momentos donde es probable que aparezcan ciclos** (para estar atentas):
- **T-13 y T-14:** casos de borde de la calculadora (₡15.000 y ₡40.000 exactos) y la zona horaria.
- **T-17:** que Gemini devuelva un JSON válido y respete el límite de 400 caracteres.
- **T-19:** la verificación de montos puede rechazar respuestas correctas si el formato del número es distinto (por ejemplo, "₡2000" contra "₡2.000").
- **T-24:** la pronunciación de montos y teléfonos.
- **T-33:** casos del conjunto de evaluación que no pasen.

---

## 6. Riesgos y plan alternativo

| ID | Riesgo | Probabilidad | Impacto | Prevención | Plan alternativo si ocurre |
|---|---|---|---|---|---|
| R-01 | **Se agotan los créditos de ElevenLabs** (10 000 caracteres al mes) antes de la demostración. | Alta | Alto | Mocks y `MODO_DEMO=true` en las fases 1 a 4; respuestas de máximo 400 caracteres; caché de audios; una sola prueba real (T-24) hasta la fase 5. | La demostración se hace con texto y con los audios que ya están en caché. Se presentan el MP3 de T-24 y su captura como evidencia de la integración real, como lo permite el laboratorio. |
| R-02 | **Se agota la cuota gratuita de Gemini** o la API responde con el error 429. | Media | Alto | Pruebas con mocks; la evaluación (T-33) se ejecuta una sola vez; botón desactivado contra envíos dobles. | Esperar a que se renueve la cuota (diaria o por minuto). Para la demostración, usar `MODO_DEMO=true` con las respuestas marcadas **[RESPUESTA SIMULADA]**, junto con las capturas de T-20 y T-33. |
| R-03 | **El modelo `gemini-3.5-flash-lite` no está disponible** en la cuenta, o cambia de nombre. | Media | Medio | Verificarlo en T-16 antes de programar. | Cambiar `GEMINI_MODEL` en `.env` por otro modelo Flash disponible (por ejemplo, `gemini-3.8-flash`), sin tocar el código. |
| R-04 | **Cambios en los SDK** de Gemini o ElevenLabs rompen el código. | Media | Medio | Versiones fijas en `requirements.txt` (T-08). | Volver a las versiones anotadas en la sección 8 y consultar la documentación oficial. |
| R-05 | **Gemini inventa datos** o cede ante una manipulación. | Media | Alto | Controles de T-19, temperatura 0.2 y conjunto de evaluación. | Ajustar el prompt, registrar el ciclo en la sección 5.2 y volver a evaluar solo los casos que fallaron. |
| R-06 | **Sin internet** en el momento de la demostración. | Baja | Alto | La calculadora y el calendario funcionan sin conexión. | `MODO_DEMO=true` y el video grabado (T-36) como respaldo. |
| R-07 | **Una clave se expone** en una captura, un commit o un prompt. | Baja | Alto | `.gitignore`, `test_seguridad.py` y revisar cada captura antes de guardarla. | Revocar la clave de inmediato en la plataforma, generar otra y limpiar el historial de Git si llegó a subirse. |
| R-08 | **La voz pronuncia mal** los montos o los teléfonos. | Media | Bajo | `normalizar_para_audio()` (T-22). | Ajustar las reglas de normalización y registrarlo como ciclo de desarrollo. |
| R-09 | **Falta de tiempo** para terminar todas las tareas. | Media | Medio | Prioridades de la sección 4. | Entregar los mínimos completos y dejar documentado lo que quedó pendiente, sin ocultarlo. |
| R-10 | **Python menor a 3.11** en la Mac. | Baja | Medio | Verificarlo en T-06. | Instalar Python 3.11 o superior desde python.org antes de continuar. |

---

## 7. Seguimiento de criterios de aceptación

Se completa en la tarea T-34.

| Funcionalidad (spec, sección 11) | Resultado | Evidencia | Observaciones |
|---|---|---|---|
| Consulta con respuesta fundamentada (≥ 18/20; HU-01 ≥ 9/10) | | | |
| Respuesta honesta sin datos (5/5) | | | |
| Resistencia a manipulación (3/3) | | | |
| Sin cálculos en el chat (3/3) | | | |
| Preguntas con dos partes (2/2) | | | |
| Coherencia de la base | | | |
| Respuestas breves (≤ 400) | | | |
| Audio automático | | | |
| Próxima fecha | | | |
| Estimado de cuenta | | | |
| Historial | | | |
| Errores amigables | | | |
| Modo demostración | | | |
| Protección de claves | | | |
| Privacidad del historial | | | |

---

## 8. Datos del entorno (se completan durante la preparación)

| Dato | Valor | Fecha de verificación |
|---|---|---|
| Versión de Python | 3.14.7 (cumple 3.11+) | 2026-11-23 |
| Repositorio GitHub | https://github.com/yeimyalvarado2708-gif/lab_2_Personal-shopper (público) | 2026-11-23 |
| Modelo de Gemini confirmado | `gemini-3.5-flash-lite` (entrada 1 048 576 tokens, salida 65 536) | 2026-11-25 |
| Límites gratuitos de Gemini vigentes | Gemini 3.5 Flash Lite: 15 solicitudes por minuto (RPM) · 250 000 tokens por minuto (TPM) · 500 solicitudes por día (RPD) | 2026-11-25 |
| Voz de ElevenLabs (nombre, no la clave) | Bella - Professional, Bright, Warm (`premade`, `hpp4J3VqNfWAUOO0d1Us`) · modelo `eleven_multilingual_v2` | 2026-11-25 |
| Créditos de ElevenLabs disponibles | Plan Free: 10 000 de 10 000 caracteres al mes · se renuevan el 2026-12-26. Después de T-24: 9 898 disponibles (102 usados). Después de T-26 y C-04: 9 455 disponibles | 2026-11-25 |
| Versiones de las dependencias (`streamlit`, `google-genai`, `elevenlabs`, `python-dotenv`, `pytest`) | streamlit 1.67.0 · google-genai 3.6.1 · elevenlabs 2.79.0 · python-dotenv 1.2.4 · pytest 9.2.0 | 2026-11-23 |

---

## 9. Historial de cambios de este plan

| Fecha | Versión | Cambio |
|---|---|---|
| 2026-11-23 | 1.0 | Versión inicial: 39 tareas en 7 fases, iteraciones de diseño D-1 a D-4 y 10 riesgos. |
| 2026-11-23 | 1.1 | T-06 y T-07 completadas; T-08 en curso (falta el commit). Se registran el repositorio y las versiones de las dependencias. |
| 2026-11-24 | 1.2 | T-06, T-08, T-09 y T-10 completadas, con sus commits y evidencias. |
| 2026-11-24 | 1.3 | T-11 completada, con su commit y evidencia. |
| 2026-11-24 | 1.4 | T-12 completada, con su commit y evidencia. |
| 2026-11-24 | 1.5 | T-13 completada, con su commit, su evidencia y las decisiones aprobadas. |
| 2026-11-24 | 1.6 | T-14 completada, con su commit y su evidencia. Termina la lógica de la calculadora. |
| 2026-11-24 | 1.7 | T-15 completada, con su commit y su evidencia. Termina la fase 1. |
| 2026-11-25 | 1.8 | T-16 en curso: modelo confirmado y clave configurada; falta anotar los límites gratuitos. Primer ciclo de desarrollo C-01 registrado. |
| 2026-11-25 | 1.9 | T-16 completada: límites gratuitos de Gemini 3.5 Flash Lite anotados (15 RPM · 250K TPM · 500 RPD). |
| 2026-11-25 | 1.10 | T-17 en curso: 20 pruebas de `gemini_client.py` aprobadas y evidencia guardada; falta el commit. |
| 2026-11-25 | 1.11 | T-17 completada, con su commit, su evidencia y las decisiones aprobadas. |
| 2026-11-25 | 1.12 | T-18 en curso: evidencia de la falta de clave (mensaje al cliente y detalle en consola). |
| 2026-11-25 | 1.13 | T-18 completada, con su commit, su evidencia y la decisión sobre los errores 500/503. |
| 2026-11-25 | 1.14 | Ciclo de desarrollo C-02 registrado (reintentos internos del SDK de Gemini, T-18). |
| 2026-11-25 | 1.15 | T-19 en curso: evidencia de los controles RF-24 y RF-21 en modo demo. |
| 2026-11-25 | 1.16 | T-19 completada, con su commit, sus pruebas y las decisiones sobre RF-24, porcentajes y recorte; referencia a `spec.md` v1.3. |
| 2026-11-25 | 1.17 | Ciclo de desarrollo C-03 registrado (mensaje fijo de RF-24 con explicación breve, T-19); falta el resultado de las pruebas. |
| 2026-11-25 | 1.18 | Resultado del ciclo C-03: 54 pruebas de `test_asistente.py` aprobadas. |
| 2026-11-25 | 1.19 | Ciclo C-03 cerrado con su commit; ajuste anotado en la fila de T-19 (387 pruebas en total); referencia a `spec.md` v1.4. |
| 2026-11-25 | 1.20 | T-20 completada: primera respuesta real de Gemini, con su fuente. Termina la fase 2. |
| 2026-11-25 | 1.21 | T-21 completada: clave de ElevenLabs con permisos mínimos, voz Bella (premade) y créditos anotados en la sección 8. |
| 2026-11-25 | 1.22 | T-22 completada: texto preparado para la voz, con las decisiones sobre símbolos y céntimos; referencia a `spec.md` v1.5. |
| 2026-11-25 | 1.23 | T-23 completada: audio con caché, sin reintentos y conectado con `responder()`; referencia a `spec.md` v1.6. |
| 2026-11-25 | 1.24 | T-24 completada: primer audio real con Bella, bien pronunciado; créditos actualizados en la sección 8. Termina la fase 3. |
| 2026-11-25 | 1.25 | T-25 completada: estructura de la pantalla y pestaña Preguntar; referencia a `spec.md` v1.8; nota sobre el commit `b7a9dd1`. |
| 2026-11-25 | 1.26 | Ajuste de diseño de T-25 (fondo, botón Enviar y pestañas, igual al prototipo). |
| 2026-11-25 | 1.27 | Ciclo de desarrollo C-04 registrado (montos en palabras para la voz, T-26); falta la confirmación al escuchar. |
| 2026-11-25 | 1.28 | T-26 completada y ciclo C-04 cerrado (audio de montos confirmado al escuchar); créditos actualizados en la sección 8. |
| 2026-11-25 | 1.29 | T-27 completada; corregida la observación de T-26 ("La carga" era la traducción de Chrome, no Gemini). |
| 2026-11-25 | 1.30 | Ajuste de T-27: página marcada en español para que Chrome no la traduzca; referencia a `spec.md` v1.12. |
| 2026-11-25 | 1.31 | T-28 completada, con el arreglo del scroll; referencia a `spec.md` v1.13. |
