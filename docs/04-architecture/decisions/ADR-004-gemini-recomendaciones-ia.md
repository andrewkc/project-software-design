# ADR-004: Gemini para recomendaciones IA de apoyo

**Estado:** Aceptado por el usuario para el prototipo. Proveedor confirmado; modelo concreto y cuota real pendientes de confirmación.

**Fecha:** 2026-11-25

## Contexto

El MVP pide sugerencias IA para reposición y descuentos, siempre sujetas a decisión del jefe (RN-08). El usuario confirmó después que el alcance incluye también **aumentos de precio** y que el proveedor debe ser **Gemini gratuito**. ChatGPT Go fue descartado porque el plan no incluye créditos de API para esta integración automática.

Solo existen datos de `precio_venta`, `stock`, `fecha_vencimiento`, `categoria` y `estado` en `ProductosBodega`/`Producto`. No hay costo, margen, historial de ventas ni predicción de vida útil. La documentación oficial de Gemini recomienda la Interactions API para proyectos nuevos y ofrece `v1` y `v1beta`. `v1` funcionó para recomendaciones de texto, pero una prueba real de REG-IA devolvió `400` porque los bloques `image` inline solo están disponibles en `v1beta`. Por eso se unificó el endpoint de ambos adaptadores en `v1beta`.

## Decisión

- Usar la **Interactions API de Gemini** desde el backend, con el endpoint `v1beta/interactions` y la cabecera `x-goog-api-key` según la documentación oficial consultada. La versión se ajustó desde `v1` el 2026-11-26 tras el error `400` real con imagen inline; `v1beta` también soporta las funciones usadas por recomendaciones.
- Modelo configurable por `GEMINI_MODEL`; default provisional: `gemini-3.1-flash-lite` (modelo disponible en `v1`/`v1beta` para tareas de alto volumen y bajo costo). Se cambió desde `gemini-3.5-flash-lite` porque la validación local devolvió `503 service_unavailable` por alta demanda. No se afirma que sea el modelo definitivo de producción.
- La clave `GEMINI_API_KEY` vive solo en el backend y se inyecta desde `.env` (ignorado por Git). Nunca se envía al navegador ni se hornea en el build de Vite.
- El prompt incluye solo los campos permitidos. La respuesta usa un esquema JSON y además se sanea en el backend: ids existentes, tipos `descuento`/`aumento`/`reposicion`, precios positivos con comparación contra el precio actual, cantidades positivas y justificación no vacía.
- Las solicitudes usan `store: false` para no retener prompts derivados del inventario.
- El endpoint `POST /recommendations/generate` es jefe-only y filtra por bodega. No persiste sugerencias, no aprueba cambios, no crea compras ni modifica stock.
- Si falta la clave o el proveedor falla, se responde `503` con mensaje claro; el inventario y las consultas básicas siguen disponibles.

## Consecuencias

### Positivas

- La decisión sigue siendo del jefe: aceptar una sugerencia abre el formulario de edición y solo se guarda si el jefe confirma.
- La clave no queda expuesta en el frontend ni en imágenes versionadas.
- La salida estructurada y el saneamiento reducen respuestas inutilizables o contradictorias con RN-09.
- El proveedor puede cambiar mediante variables de entorno sin reescribir el cliente.

### Negativas / riesgos

- Las cuotas gratuitas no están garantizadas y deben revisarse en el proyecto del usuario (`https://aistudio.google.com/rate-limit`).
- Sin historial de ventas ni costos, las justificaciones son explicaciones de los campos disponibles, no predicciones validadas.
- Queda pendiente decidir si EN-08 se persistirá para auditoría de decisiones; este corte no lo hace.
- Las promociones con vigencia siguen fuera del corte; aquí solo se revisa precio.

## Alternativas consideradas

- **ChatGPT Go:** descartada; el plan no aporta créditos de API para esta integración automática.
- **Reglas fijas locales:** no cumplirían la decisión del usuario de usar IA; el prototipo huérfano con 10% fijo no se reutilizó como lógica real.
- **Sin IA:** mantiene inventario disponible, pero no atiende el alcance confirmado.

## Trazabilidad

CU-08, CU-09; RF-12, RF-13, RF-14, RF-24; RN-07, RN-08, RN-09; EN-03, EN-04, EN-07, EN-08; [REC-IA](../../05-specifications/recomendaciones-ia/spec.md).
