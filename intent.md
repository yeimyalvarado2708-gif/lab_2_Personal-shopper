# intent.md — Asistente de atención al cliente con voz para "Personal Shopper"

**Laboratorio 2 · Desafío 1 · LE Claude Code**
**Autora:** Yeimy Alvarado
**Fecha:** 2026-11-23
**Versión:** 1.1 (1.1: alcance y privacidad alineados con la decisión D-02 del spec, en la revisión final T-39 del 2026-11-26)

---

## 1. Problema real

"Personal Shopper" es un emprendimiento de Guápiles, Pococí, que compra productos por encargo en PriceSmart San José y los entrega en Guápiles y alrededores. Los clientes hacen sus consultas por WhatsApp, y la mayoría son siempre las mismas: cómo funciona el servicio, cuánto se cobra, qué día se va a PriceSmart, dónde se entrega, si hay entrega a domicilio y cuánto cuesta, cómo y a qué número se paga, y hasta cuándo se recibe la lista.

La dueña es la única persona que atiende el negocio, así que contesta cada consulta a mano. Eso tiene tres consecuencias:

- **Pierde tiempo** escribiendo la misma información una y otra vez, sobre todo los miércoles (cierre de pedidos) y los jueves (día de compra), que son los días de más trabajo.
- **Las respuestas pueden variar o tener errores**, por ejemplo con los porcentajes por rango de factura o con las zonas donde la entrega a domicilio cuesta ₡2.000.
- **Los clientes esperan**, porque mientras ella está comprando en PriceSmart no puede contestar enseguida.

## 2. Usuarios objetivo

| Usuario | Descripción | Qué necesita |
|---|---|---|
| **Cliente nuevo** | Persona de Guápiles que se entera del servicio y quiere saber cómo funciona antes de hacer su primer pedido. | Una explicación clara del proceso, las tarifas, la cortesía de la primera compra y los medios de pago. |
| **Cliente frecuente** | Persona que ya compra con el servicio y tiene dudas puntuales. | Respuestas rápidas sobre la próxima fecha de compra, el cierre de la lista, el número de SINPE o el costo de entrega en su zona. |
| **Dueña del emprendimiento** | Única operadora del negocio. | Menos mensajes repetitivos, información siempre consistente y saber cuándo una consulta necesita su atención personal. |

## 3. Valor esperado

- Los clientes reciben **respuestas inmediatas** a las preguntas frecuentes, en texto y en audio, a cualquier hora.
- Las respuestas son **consistentes y verificables**: salen siempre de una base de conocimiento única (`data/base_conocimiento.json`) que mantiene la dueña.
- **Los cálculos no dependen del modelo:** el estimado de la cuenta y la próxima fecha de compra se calculan en Python con reglas fijas.
- **El asistente no inventa:** cuando la información no está en la base, lo dice y remite a la dueña por WhatsApp.
- **El audio** facilita la consulta a quienes prefieren escuchar en lugar de leer.

## 4. Objetivos

### Objetivo general

Desarrollar un asistente de atención al cliente con voz que responda las preguntas frecuentes del emprendimiento "Personal Shopper" usando únicamente una base de conocimiento local. Gemini redacta las respuestas, ElevenLabs las convierte en audio, y el asistente indica claramente cuándo no tiene información suficiente.

### Objetivos específicos

1. **Responder con base en datos verificables:** construir una base de conocimiento local con 23 preguntas y respuestas sobre el servicio, y lograr que Gemini responda solo con esa información, citando la pregunta de origen (FAQ-XX).
2. **Calcular en Python, no con el modelo:** implementar funciones que estimen el total de la cuenta (cargo del servicio por rango, cortesía de primera compra, ₡2.000 en zonas con cargo) y que determinen la próxima fecha de compra, con pruebas automatizadas que no dependan de las API.
3. **Ofrecer respuesta en voz y manejar los fallos:** convertir cada respuesta en audio con ElevenLabs, guardar un historial de al menos cinco interacciones y mostrar mensajes amigables cuando Gemini o ElevenLabs no estén disponibles.

## 5. Alcance del MVP

### Incluye

- Una interfaz web local hecha con Streamlit, donde el cliente escribe su pregunta.
- El envío de la base de conocimiento completa (`data/base_conocimiento.json`) a Gemini en cada consulta, porque es pequeña y no tiene datos sensibles (decisión D-02 del spec). La búsqueda por palabras clave se usa solo en el modo demostración.
- La generación de la respuesta con Gemini, limitada a la información de la base.
- Un mensaje explícito cuando no hay datos suficientes, con remisión a WhatsApp (derivación a la dueña).
- La conversión de la respuesta en audio con ElevenLabs y su reproducción en la interfaz.
- Un historial de al menos cinco interacciones durante la sesión.
- Una calculadora de estimado de cuenta: monto aproximado, zona y si es la primera compra.
- El cálculo de la próxima fecha de compra (jueves) y de la fecha límite de la lista (miércoles), tomando en cuenta las semanas canceladas.
- Mensajes de error amigables cuando falte la clave, no haya conexión o se haya agotado la cuota.
- **Reto adicional:** la categoría de cada consulta y la trazabilidad de la fuente (qué FAQ respaldó la respuesta).

### No incluye

- Integración real con WhatsApp ni respuestas automáticas en ese canal.
- Recibir pedidos, procesar pagos o confirmar depósitos.
- Consultar el inventario real de PriceSmart. El asistente explica cómo verificar si hay un producto, pero no lo comprueba.
- Calcular la cuenta real de un cliente. El total exacto lo envía la dueña el jueves desde la tienda; el asistente solo ofrece un **estimado**.
- Reconocimiento de voz: el cliente escribe, no habla.
- Clonación de voz: se usa una voz estándar del plan gratuito.

## 6. Historias de usuario

### HU-01 — Consultar cómo funciona el servicio y cuánto cuesta

**Como** cliente nuevo, **quiero** preguntar cómo funciona el servicio y cuánto se cobra, **para** decidir si hago mi primer pedido.

**Criterios de aceptación:**
- Al preguntar "¿cómo funciona el servicio?" o "¿cuánto cobran?", la respuesta incluye el proceso (lista hasta el miércoles, compra el jueves, pago antes de pasar por cajas) y los tres rangos de cobro (20%, 15% y 10%).
- La respuesta muestra la fuente usada (por ejemplo, FAQ-01 y FAQ-02).
- La respuesta se reproduce en audio en la misma pantalla.
- De un conjunto de 10 preguntas de prueba sobre servicio y tarifas, al menos 9 se responden correctamente según la base de conocimiento.

### HU-02 — Estimar mi cuenta y saber la próxima fecha de compra

**Como** cliente frecuente, **quiero** saber cuándo es la próxima compra y cuánto pagaría aproximadamente, **para** preparar mi lista y mi dinero a tiempo.

**Criterios de aceptación:**
- Al preguntar "¿cuándo es la próxima compra?", el asistente muestra la fecha del próximo jueves (o la siguiente semana disponible, si ese jueves está cancelado) y la fecha límite para enviar la lista.
- Al ingresar un monto, la zona y si es la primera compra, la calculadora devuelve un estimado que coincide al 100% con el cálculo manual en estos casos de prueba:
  - ₡10.000, zona sin cargo → ₡12.000 (20%)
  - ₡30.000, La Trocha → ₡36.500 (15% + ₡2.000)
  - ₡50.000, zona sin cargo → ₡55.000 (10%)
  - ₡30.000, primera compra, zona sin cargo → ₡30.000 (cortesía)
- El resultado se presenta como **estimado** e indica que el total exacto lo envía la dueña el jueves.
- Si el monto es vacío, negativo o no numérico, se muestra un mensaje de validación y no se hace ningún cálculo.

### HU-03 — Recibir una respuesta honesta cuando no hay información

**Como** cliente, **quiero** que el asistente me diga claramente cuando no sabe algo, **para** no recibir información falsa y saber a quién preguntarle.

**Criterios de aceptación:**
- Ante preguntas que no están en la base (por ejemplo, "¿venden ropa?" o "¿entregan en Limón centro?"), el asistente responde que no tiene información suficiente y remite al WhatsApp de contacto.
- De 5 preguntas de prueba fuera de la base, el 100% recibe este tipo de respuesta y ninguna recibe datos inventados.
- Si Gemini falla (falta la clave, no hay conexión o se agotó la cuota), aparece un mensaje amigable y la aplicación no se cierra.
- Si ElevenLabs falla, la respuesta en texto se muestra igual, con un aviso de que el audio no está disponible.

## 7. Restricciones

| Tipo | Restricción |
|---|---|
| **Costo** | Solo planes gratuitos: Gemini API mediante Google AI Studio y ElevenLabs Free. Cero costo de operación para el MVP. |
| **Límites de API** | Los créditos y solicitudes de los planes gratuitos son limitados y pueden cambiar. Se deben verificar en cada plataforma antes de empezar. Para cuidar los créditos, el audio se genera solo con respuestas cortas, y las pruebas automatizadas usan *mocks* en lugar de llamadas reales. |
| **Privacidad** | No se usan datos personales reales: el número de SINPE y el de WhatsApp son ficticios (8888-0000) y no se guardan números de cuenta. Las claves API viven solo en `.env`, que está excluido de Git con `.gitignore`. A Gemini solo se le envía la pregunta y la base de conocimiento, nunca datos de clientes guardados por el negocio. |
| **Conectividad** | La aplicación necesita internet para Gemini y ElevenLabs. Sin conexión, la calculadora y la próxima fecha siguen funcionando porque son locales, y se muestra un aviso para la parte de IA. Si se agota el crédito, se presenta una demostración con respuestas simuladas claramente identificadas. |
| **Tiempo** | El proyecto se desarrolla individualmente dentro del plazo del laboratorio. Se prioriza cumplir los mínimos funcionales antes que el reto adicional. |
| **Técnicas** | Python 3.11+, Streamlit, el SDK oficial de Gemini, la API de ElevenLabs, Git/GitHub y Visual Studio Code con Claude Code. |

## 8. Definición de éxito

La solución se considera exitosa si cumple **todas** estas condiciones:

1. **Responde con datos:** de un conjunto de 20 preguntas de prueba que sí están en la base, al menos 18 (90%) se responden correctamente y con la FAQ de origen indicada.
2. **No inventa:** las 5 preguntas de prueba fuera de la base reciben el mensaje de "no tengo información suficiente" (100%).
3. **Calcula bien:** las pruebas automatizadas de `calcular_cuenta()` y de la función de próxima fecha pasan en su totalidad, sin llamar a las API.
4. **Habla:** cada respuesta válida genera un audio que se puede reproducir en la interfaz.
5. **Recuerda:** el historial muestra al menos las últimas cinco interacciones de la sesión.
6. **Falla con elegancia:** al simular la falta de clave, un fallo de red y la cuota agotada, la aplicación muestra mensajes amigables y no se cierra.
7. **Protege las claves:** se verifica que `.env` no está en el repositorio y que `.env.example` no contiene secretos.

La verificación se documentará con capturas o un video que muestren el texto generado, el audio y el manejo de al menos un error, además del resultado de `pytest`.
