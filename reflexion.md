# Reflexión · Asistente con voz "Personal Shopper"

**Laboratorio 2 · Desafío 1 · LE Claude Code** · Yeimy Alvarado · 2026-11-26

## Decisiones humanas

Diseñé esta aplicación a partir de las necesidades reales de mi emprendimiento de compras en PriceSmart. Ya tenía una app para gestionar los pedidos y cobrar por WhatsApp, con los precios, los cálculos y el total; este proyecto me permitió crear otra herramienta, ahora para la atención al cliente: responder las preguntas frecuentes cuando me contactan. Construí la base de conocimiento con la información de mi negocio y diseñé el front-end.

Me importaba que la app se sintiera como si yo estuviera frente al cliente. No quería una herramienta para evitar el contacto conmigo, sino un asistente que le da información precisa y rápida y que, si no queda satisfecho, le ofrece el enlace de WhatsApp para continuar sus consultas directamente conmigo. Por eso elegí un trato respetuoso, de "usted", en la redacción de todos los mensajes, y una voz amigable pero profesional. Además, revisé uno por uno los audios generados, para asegurarme de que el cliente escuchara lo que yo quería transmitir.

## Limitaciones del modelo

Muchas limitaciones vienen de los planes gratuitos: limité las respuestas a 400 caracteres para cuidar los créditos. Además, el modelo no siempre entiende como yo esperaba: a "¿Cuánto cuesta un televisor?" respondió cómo verificar si hay un producto, y en otra prueba agregó una razón que no estaba en mi base. Por eso no basta con el prompt: hay que revisar cada respuesta. En el futuro, el asistente podría aceptar consultas por voz y conectarse con una API de PriceSmart.

## Seguridad

Se cumplieron los requisitos del laboratorio: las claves de API se guardan únicamente en el archivo `.env`, que nunca se subió a Git ni a GitHub. En el repositorio solo está `.env.example`, sin ningún secreto.

## Aprendizajes

Este proyecto me ayudó a estructurar una forma responsable de programar con IA. El archivo `intent.md` fue el que más trabajo me llevó, porque ahí plasmé la intención y los objetivos de lo que quería construir. Con `spec.md` establecí las reglas técnicas del programa, y con `plan.md` seguí un ritmo de trabajo que me permitió ver, detalle a detalle, cómo se generaba el código, revisarlo y ajustarlo para que la app fuera más clara y tuviera menos errores. También aprendí a establecer pruebas con mocks, que permiten probar la app sin gastar créditos. Sobre todo, entendí que trabajar así me permite saber dónde están los problemas cuando la app necesite mantenimiento: ser la dueña de mi propio programa.

---

**Conteo de palabras:** 396 (texto de las cuatro secciones, sin títulos; contadas con `split()` de Python).
