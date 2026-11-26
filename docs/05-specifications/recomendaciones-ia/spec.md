# REC-IA — Recomendaciones IA para la decisión del jefe

**Estado:** Implementado en el prototipo; pendiente de validación con una clave real de Gemini. No es una funcionalidad validada en producción.

## Identificador y trazabilidad

`REC-IA` es un identificador técnico de esta especificación incrementable. No sustituye a los casos de uso del negocio: amplía **CU-08** (precios, descuentos y promociones) y **CU-09** (reposición), y registra la expansión de alcance acordada para incluir también **aumentos de precio**.

## Problema y objetivo

**Confirmado:** el jefe necesita apoyo para revisar precios y reposición, sin que un sistema automático tome la decisión. Las entrevistas son exploratorias y no demuestran que las recomendaciones reduzcan pérdidas.

**Objetivo del incremento:** ofrecer sugerencias informativas generadas bajo demanda, explicadas con los campos que ya existen en la bodega, y dejar siempre la decisión y la escritura al jefe.

## Alcance incluido / excluido

### Incluido

- Sugerencias de **descuento**, **aumento de precio** y **reposición referencial**. La inclusión de aumentos es una expansión de alcance confirmada por el usuario y debe reflejarse en CU-08/RF-12.
- Generación bajo demanda desde una sección visible solo para el jefe.
- Envío a Gemini únicamente de `nombre`, `categoria`, `stock`, `precio_venta`, `fecha_vencimiento` y `estado` de productos activos de la bodega del jefe.
- Respuesta estructurada con tipo, identificador de producto, valor sugerido y justificación breve.
- Revisión manual: al aceptar una sugerencia de precio se abre el formulario de edición con el valor sugerido; el jefe puede modificarlo y guardar mediante `PATCH /products/{id}`.
- Mensaje explícito de que la IA no aprueba cambios, no genera compras ni modifica inventario.
- Fallo controlado (`503`) si la clave o el proveedor no están disponibles; el inventario y las consultas siguen funcionando.

### Excluido

- Aplicación automática de precios, descuentos o cantidades.
- Generación de órdenes de compra, movimientos de inventario o promociones con vigencia.
- Costos, márgenes, historial de ventas, predicción de vida útil ni estimaciones de demanda validadas.
- Persistencia de sugerencias, decisiones o justificaciones en una tabla nueva dentro de este corte.
- Proveedores, pagos, facturación, entregas, contabilidad, voz/fotografía operativa ni vista pública.

## Actores y permisos

| Actor | Permiso |
|---|---|
| Jefe (AN-02) | Puede pedir, ver, modificar y guardar manualmente las sugerencias de su bodega. Hereda las operaciones del empleado según RN-02. |
| Empleado (AN-03) | No ve la sección; el backend devuelve `403` aunque llame directamente al endpoint. |
| Gemini | Solo genera texto estructurado. No es aprobador, no escribe en la base y no ejecuta acciones (RN-08). |

## Precondiciones y postcondiciones

**Precondiciones:** sesión válida de jefe; bodega asociada; al menos un producto activo; `GEMINI_API_KEY` configurada en el backend.

**Postcondiciones:** no se crea, actualiza ni elimina ninguna fila al generar. Solo se cambia un precio cuando el jefe envía explícitamente `PATCH /products/{id}`. Una reposición revisada no cambia `stock` ni crea movimientos.

## Flujo principal

1. El jefe abre **Recomendaciones** y pulsa *Generar recomendaciones*.
2. El backend valida rol y bodega, consulta productos activos y envía a Gemini solo los campos permitidos con un esquema JSON.
3. El backend descarta sugerencias inconsistentes o inventadas y devuelve `generadas_en`, `modelo`, `recomendaciones` y `aviso`.
4. La interfaz muestra cada propuesta con su justificación y el aviso de no validación.
5. Para descuentos y aumentos, *Revisar precio* abre el formulario existente con el precio sugerido. El jefe puede cambiarlo y guardar. Para reposición solo se muestra información de referencia.

## Alternativas y excepciones

| Situación | Comportamiento |
|---|---|
| Empleado llama al endpoint | `403`; no se contacta al proveedor. |
| Falta `GEMINI_API_KEY` | `503` con mensaje claro; la UI muestra el error y mantiene el inventario utilizable. |
| Gemini no responde o devuelve JSON inválido | `503`; no se muestran sugerencias parciales como válidas. |
| Sugerencia con id ajeno, tipo desconocido, precio no positivo, descuento mayor o igual al actual, aumento menor o igual al actual, cantidad no positiva o justificación vacía | Se descarta durante el saneamiento. |
| No hay productos activos o no hay propuestas válidas | Respuesta correcta con lista vacía y mensaje de estado vacío en la UI. |

## Reglas de negocio

- **RN-02:** cada cuenta opera solo sobre su bodega; el jefe puede ejecutar operaciones del empleado.
- **RN-07:** el jefe modifica precios; la IA nunca aprueba descuentos ni promociones.
- **RN-08:** toda sugerencia requiere aprobación del jefe, quien puede modificarla o rechazarla. Reposición aprobada no genera compra ni cambia stock.
- **RN-09:** un descuento debe ser un precio positivo menor al actual. Por expansión acordada, un aumento debe ser un precio positivo mayor al actual.
- El backend usa un esquema de salida y además valida los valores antes de responder. La validación del modelo no se considera suficiente por sí sola.

## Datos y entidades

- **EN-03 / EN-04:** se usan `precio_venta`, `stock`, `fecha_vencimiento`, `categoria` y `estado` disponibles en la bodega; no se incorpora `costo`.
- **EN-07:** las promociones con vigencia quedan fuera de este incremento; aquí solo se revisa precio.
- **EN-08:** la sugerencia existe solo en la respuesta. No hay tabla, estado de decisión ni fecha de aprobación persistidos en este corte.
- **ADR-004:** proveedor Gemini, clave solo en backend y modelo configurable.

## Criterios de aceptación

- [ ] El jefe ve la navegación a Recomendaciones; el empleado no la ve y recibe `403` si llama al endpoint.
- [ ] `POST /recommendations/generate` devuelve solo sugerencias saneadas, con `aviso` y sin escribir en la base.
- [ ] Los campos enviados a Gemini son exactamente los permitidos; la clave nunca aparece en el frontend.
- [ ] Un descuento es menor al precio actual; un aumento es mayor; una reposición tiene cantidad positiva y no modifica stock.
- [ ] Al aceptar un precio se abre el formulario; nada se guarda hasta que el jefe lo confirma.
- [ ] Sin clave o sin proveedor, la respuesta es `503` y el inventario sigue disponible.
- [ ] Las pruebas estáticas, unitarias y HTTP pasan con la clave real configurada.

## Escenarios de prueba

| Escenario | Resultado esperado |
|---|---|
| Generar como jefe con clave válida | Lista saneada con justificación y aviso; productos sin cambios. |
| Generar como empleado | `403`. |
| Generar sin clave | `503`; sin mutación. |
| IA devuelve id inexistente o precio igual al actual | Descartado por `_sanitize`. |
| IA devuelve reposición válida | Se muestra como referencia; no hay `POST` de compra ni cambio de stock. |
| Jefe revisa precio y guarda | Se llama a `PATCH /products/{id}`; la decisión queda registrada como acción del jefe en la UI. |

## Dependencias

- Backend FastAPI existente, token HMAC, `bodega_id_for` y `PATCH /products/{id}`.
- Variable de entorno `GEMINI_API_KEY` inyectada por `docker-compose.yml` desde `.env` ignorado por Git.
- Modelo con salidas estructuradas; default provisional `gemini-3.1-flash-lite`. Se cambió desde `gemini-3.5-flash-lite` porque la prueba real devolvió `503 service_unavailable` por alta demanda.
- Cuotas del tier gratuito: **pendiente** de verificar en el proyecto del usuario.

## Preguntas abiertas

1. ¿Qué modelo exacto se usará en producción? El default es una recomendación derivada, no una decisión confirmada.
2. ¿Se persistirán las decisiones de sugerencias (EN-08) o bastará con el cambio de precio? Afectaría a CU-08/CU-09 y a RF-12/RF-13.
3. ¿Cómo se medirá utilidad o precisión sin historial de ventas? Sigue abierta la pregunta 17 de `open-questions.md`.
4. ¿Se crearán promociones con vigencia a partir de un descuento? Queda fuera de este corte.
5. ¿Cuál es la cuota real disponible en la cuenta Gemini del usuario?

## Trazabilidad

| Caso | Requisitos | Reglas | Entidades | Decisión | Código / pruebas |
|---|---|---|---|---|---|
| CU-08, CU-09 | RF-11…RF-14, RF-24 | RN-02, RN-07, RN-08, RN-09 | EN-03, EN-04, EN-07, EN-08 | ADR-004 | `apps/backend/ai.py`, `apps/backend/routers/recommendations.py`, `apps/operations-web/src/features/recommendations/RecommendationsPage.jsx`, `tests/test_ai_recommendations.py`, `tests/test_backend_api.py` |
