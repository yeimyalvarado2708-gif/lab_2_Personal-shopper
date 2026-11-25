# plan.md — Plan de implementación del Asistente "Personal Shopper"

**Laboratorio 4 · Desafío 1 · LE Claude Code**
**Autora:** Yeimy Alvarado
**Fecha de inicio:** 2026-11-23
**Versión:** 1.5
**Documentos relacionados:** `intent.md` v1.0 · `spec.md` v1.1 · `data/base_conocimiento.json` v1.4 · `tests/preguntas_evaluacion.json` v1.0

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
| T-14 | `src/calculadora.py`: `proxima_fecha_compra()` y `hoy_costa_rica()` (zona horaria y máximo de 8 semanas). | RF-12, RF-28, RF-29 | Claude Code | ⬜ | Los 5 casos de fechas y el caso de zona horaria pasan. |
| T-15 | `src/demo.py`: respuestas simuladas por palabras clave, sin distinguir mayúsculas ni tildes. | RF-20, RF-30 | Claude Code | ⬜ | `test_demo.py` pasa. |

### Fase 2 — Integración con Gemini

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-16 | Obtener la clave en Google AI Studio, confirmar que `gemini-3.5-flash-lite` está disponible y anotar los límites gratuitos vigentes. | Pendiente del spec | Yeimy | ⬜ | Clave en `.env` (nunca en capturas); límites anotados en la sección 8. |
| T-17 | `src/gemini_client.py`: prompt con delimitadores, respuesta en JSON, temperatura 0.2 y tiempo de espera. | RF-04, RF-05, RF-22, RF-23, RNF-12, RNF-13 | Claude Code | ⬜ | `test_gemini_client.py` (con mocks) pasa. |
| T-18 | Traducir los errores de Gemini (falta de clave, clave inválida, red, cuota, JSON inválido) a las excepciones propias. | RF-18, sección 7 | Claude Code | ⬜ | Las pruebas de error con mock pasan. |
| T-19 | `src/asistente.py`: controles anti-invención (fuentes, mensaje fijo, verificación de montos, dos partes, recorte a 400). | RF-06, RF-07, RF-10, RF-21, RF-24, RF-25 | Claude Code | ⬜ | `test_asistente.py` pasa. |
| T-20 | **Primera prueba real de Gemini:** una pregunta desde la consola, con `MODO_DEMO=false`. | Prueba manual 1 | Yeimy | ⬜ | Captura de la respuesta con su fuente, guardada en `evidencias/`. |

### Fase 3 — Integración con ElevenLabs

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-21 | Obtener la clave de ElevenLabs, elegir una voz **prediseñada (premade)** y anotar su `voice_id` en `.env`. Revisar los créditos del mes. | Pendiente del spec | Yeimy | ⬜ | Créditos disponibles anotados en la sección 8. |
| T-22 | `voz.normalizar_para_audio()`: montos, teléfonos y símbolos. | RF-26 | Claude Code | ⬜ | Los 4 casos de 5.6.1 del spec pasan. |
| T-23 | `src/voz.py`: llamada a ElevenLabs, caché en `cache_audio/`, tiempo de espera y traducción de errores. | RF-09, RF-11, RF-19, RNF-12 | Claude Code | ⬜ | `test_voz.py` (con mocks) pasa. |
| T-24 | **Primera prueba real de audio:** generar un audio con monto y teléfono, y escucharlo. | Pruebas manuales 2 y 6 | Yeimy | ⬜ | Archivo MP3 y nota de cómo se pronunció, en `evidencias/`. |

### Fase 4 — Interfaz (Streamlit)

| ID | Tarea | Requisitos | Responsable | Estado | Evidencia de terminación |
|---|---|---|---|---|---|
| T-25 | `app.py`: chat con campo de pregunta, botón Enviar (desactivado mientras procesa), respuesta, fuente y categoría. | RF-01, RF-08, RF-31 | Claude Code | ⬜ | La app abre con `streamlit run app.py` y responde en modo demo. |
| T-26 | Reproductor de audio (sin reproducción automática) y avisos cuando el audio no está disponible. | RF-09, RF-19, D-03 | Claude Code | ⬜ | Captura de una respuesta con reproductor. |
| T-27 | Formulario de la calculadora de estimado, con su desglose y leyenda. | RF-13 a RF-16 | Claude Code | ⬜ | Captura del caso ₡30.000 en La Trocha = ₡36.500. |
| T-28 | Historial de la sesión (mínimo 5, del más reciente al más antiguo, solo en memoria). | RF-17, RNF-15 | Claude Code | ⬜ | Captura después de 6 consultas. |
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
| **C-01** | | | | | | | |
| **C-02** | | | | | | | |
| **C-03** | | | | | | | |
| **C-04** | | | | | | | |

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
| Modelo de Gemini confirmado | | |
| Límites gratuitos de Gemini vigentes | | |
| Voz de ElevenLabs (nombre, no la clave) | | |
| Créditos de ElevenLabs disponibles | | |
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
