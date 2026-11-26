# Calidad y validación

Áreas mínimas derivadas: permisos por rol y aislamiento por bodega; cantidades positivas; disponibilidad de lotes; consistencia de entradas/salidas; descuento de stock exactamente una vez; prohibición de vender vencidos/deteriorados; cálculo de venta; vigencia y restricciones de promociones; aprobación explícita de sugerencias; reposición aprobada sin compra ni cambio de stock.

## Validación de recomendaciones IA (REC-IA)

- Unitaria sin red: `tests/test_ai_recommendations.py` revisa el contrato de la solicitud, el saneamiento de descuentos/aumentos/reposiciones, el límite de sugerencias, los formatos de respuesta aceptados, el fallo sin clave, la ausencia de escrituras en la base y que la clave no llegue al frontend.
- Estática de contrato: `tests/test_endpoint_usage.py` comprueba la paridad entre rutas del backend y llamadas de `api.js`, incluida `POST /recommendations/generate`.
- Integración HTTP: `tests/test_backend_api.py` agrega `403` para empleado y verifica que generar recomendaciones no modifique precios ni stock.
- Errores del proveedor: el adaptador incluye un fragmento del cuerpo devuelto por Gemini en el `503`, con la clave redactada, para diagnosticar cuotas/modelo sin exponer secretos.
- Hallazgo de la prueba local: `gemini-3.5-flash-lite` devolvió `503 service_unavailable` por alta demanda; el default provisional pasó a `gemini-3.1-flash-lite` y queda pendiente una corrida estable con clave real.
- Hallazgo de la prueba real de REG-IA: `v1/interactions` devolvió `400` porque `input[1].type = "image"` solo existe en `v1beta`. El default compartido de `GEMINI_API_URL` pasó a `v1beta/interactions` en `config.py` y `docker-compose.yml`; la documentación y las pruebas estáticas se alinearon. Falta repetir la prueba con la mandarina sintética/propia.
- Hallazgo de la prueba real de `Código`: `google_search` devolvió `429 too_many_requests` porque *Search grounding* no está disponible en el plan gratuito de `gemini-3.1-flash-lite`. Por decisión del usuario se eliminó esa herramienta y el modo pasó a consultar Open Food Facts con los dígitos procesados; si no hay coincidencia, responde “No se encontró en la base de datos. Regístralo manualmente.”
- UI de recomendaciones: el estado vive en `App.jsx`, por lo que las tarjetas sobreviven al cambio de sección; el botón cambia a “Volver a generar recomendaciones” con estilo `button-soft`; cada tarjeta muestra el `icono` del producto a la izquierda del nombre. El icono se agrega en el saneamiento del backend y no se envía a Gemini.
- No mutación: la generación no persiste sugerencias; el único cambio ocurre si el jefe confirma manualmente `PATCH /products/{id}`.

## Validación de registro asistido (REG-IA)

- Unitaria sin red: `tests/test_registration_ai.py` cubre el request multimodal de `Foto`/`Voz`, la validación de MIME/tamaño/base64, el saneamiento por modo (RN-12/RN-13/RN-14), la consulta a Open Food Facts con `User-Agent`/timeout, el caso “no encontrado”, la ausencia de `google_search` y el error `503` con clave redactada. `Voz` cubre los ocho campos dictados, con precio/fecha solo si se dicen y sin estimación de vencimiento. `Código` no propone `cantidad`, `precio_venta` ni `fecha_vencimiento` porque Open Food Facts no los expone.
- Categorías: las pruebas cubren las nueve categorías base compartidas por seed/UI/`CATEGORIAS`, la creación y reutilización con normalización case-insensitive, la migración deduplicada de `Producto` y la persistencia estática del esquema y de las rutas `GET/POST /categories`.
- Emojis y cámara: las pruebas cubren la paridad exacta entre `PRODUCT_EMOJIS` e `ICONOS` y la alternancia del botón del medio de `Código` entre captura con cámara lista y reinicio de cámara, sin quitar «Subir imagen» ni «Leer dígitos».
- Estática de contrato: `tests/test_endpoint_usage.py` incluye `POST /products/extract`, `GET /ai/models`, `GET/POST /categories` y sus helpers en `api.js`; además comprueba que el frontend no lee `GEMINI_API_KEY`.
- Selector de modelo: las pruebas unitarias comprueban que `resolve_model()` acepta vacío/default y rechaza ids fuera de la allowlist, que el cuerpo de Gemini y la respuesta usan el modelo elegido, y que el selector del frontend no contiene clave ni URL del proveedor. `GET /ai/models` solo expone `{id, label, activo}` y `default`.
- Integración HTTP: `tests/test_backend_api.py` verifica `400` con datos inválidos, que la extracción no modifica productos y `test_categories_can_grow_and_are_reused`.
- Interfaz: `ProductForm` es controlado y no contiene el prefill de demostración; `VoiceCapture` usa `MediaRecorder` real, `PhotoCapture`/`BarcodeCapture` entregan dataURL y `CategoryPicker` ofrece búsqueda y «Agregar nueva categoría». `AiModelPicker` aparece solo en `Foto`/`Voz`, tanto en `RegisterPage` como en `ProductModal`.
- Privacidad: las pruebas con clave real deben usar solo multimedia sintético o propio, según ADR-005.
- **Estado:** pruebas actualizadas en código; **no ejecutadas en este entorno**. No se afirma que pasan ni que el producto esté terminado.

## Validación de ventas (VENTAS-01)

- Estática de contrato: `tests/test_sales.py` revisa el esquema y el servicio (solo `pagado`, `FOR UPDATE`, descuento condicional, idempotencia, savepoint de la demo, filtro por bodega en `GET/POST /sales`, navegación visible para jefe y empleado y `api.js`), además de la recarga de ventas/inventario al enfocar la pestaña y el botón «Actualizar».
- Integración HTTP: `tests/test_backend_api.py` agrega permisos `403` para `cliente`, rechazo de cantidades mayores que el stock y verificación de que un pedido no pagado no aparece en `/sales`.
- Coherencia: cada venta se guarda con `Compra.estado = 'pagado'`, detalle con precios congelados, `ReservaCompra` consumida y traza `Pago` local; el stock baja en el mismo `UPDATE ... WHERE stock >= cantidad`.
- Demo: tres compras sintéticas con claves UUID fijas; `ensure_demo_sales()` consulta la clave antes de insertar y usa un savepoint por compra, por lo que un reinicio no duplica el descuento.
- Privacidad: la vista solo muestra nombre y apellido del comprador; no hay correo, teléfono ni pasarela externa.
- **Estado:** código y pruebas actualizados; **no ejecutados en este entorno**. Falta verificar en navegador que `Ventas` aparece para jefe y empleado, que el stock baja una sola vez y que no se filtra `GEMINI_API_KEY` al bundle.

## Validación de la tienda del comprador (CLIENTE-01)

- Estática de contrato: `tests/test_customer_contract.py` revisa el registro del router, la bandera de pago simulado, el menú de cuatro secciones (sin entrada duplicada `Perfil`; en móvil se abre «Mi cuenta» desde el panel desplegable), el rol `Cliente`, los tokens visuales compartidos, el historial con todos los estados, el catálogo de ofertas derivado de `ProductosBodega`, que no exista ruta de compra local y que el descuento de stock viva solo en `sales_service.py`.
- Cobertura de rutas: `tests/test_endpoint_usage.py` incluye las llamadas de `apps/customer-web/src/lib/api.js` con el prefijo `/customer`, ahora también `GET /payment-methods`; el webhook queda declarado como endpoint servidor-a-servidor no llamado por el navegador.
- Interfaz: `tests/test_customer_contract.py` comprueba que los logos oficiales se copian a `public/assets`, se sirven en `Brand.jsx` y quedan directos sobre el verde en el acceso; también verifica el botón del logo interno sin borde/fondo, la escala `1.2` de login/registro en escritorio y los márgenes compactos para evitar desplazamiento.
- Integración con base desechable: `tests/test_customer_flow.py` se omite salvo que `BODESMART_TEST_DATABASE_URL` iguale a `DATABASE_URL`; cubre reserva sin descuento, idempotencia, una sola bodega, expiración, rechazo, pago local exactamente once, verificación externa del importe y de la cuenta, y webhook firmado.
- Stock: `Simular pago` y `verify-payment` pasan por `approve_reserved_order()`; la aprobación consume la reserva, fija `fecha_pago` y limpia `reserva_hasta`, igual que `POST /sales`. Un cobro acreditado tarde queda `pago_en_revision` sin tocar inventario.
- **Estado:** código y pruebas escritos; **no ejecutados en este entorno**. Falta validar el checkout de prueba en navegador y con credenciales reales de Mercado Pago de prueba.

## Validación del panel administrativo (ADMIN-01)

- Estática de contrato: `tests/test_admin_contract.py` revisa las siete rutas, el guard que impide editar/desactivar a otro admin, la baja lógica, que las respuestas no incluyan contraseñas, las migraciones idempotentes, el token aislado de `admin-web`, los Dockerfiles (usan `npm install`; el lockfile se genera en local), el build arg de la API, la nav móvil oculta en escritorio, el perfil accesible solo desde la tarjeta inferior y la exposición de `admin-web` en compose/`.env.example`.
- Cobertura de rutas: `tests/test_endpoint_usage.py` incluye `apps/admin-web/src/lib/api.js`, por lo que cada endpoint `/admin/*` debe tener consumo en el frontend.
- Interfaz: `tests/test_admin_contract.py` comprueba que los logos oficiales se copian a `admin-web/public/assets`, se sirven en `Brand.jsx` (completo directo sobre el verde en el acceso, compacto en sidebar/móvil) y que el login usa un escalado compacto en escritorio para no requerir desplazamiento.
- Regresión: `/auth/login`, `/auth/me`, `/profiles/*` y `/customer/*` conservan sus rutas; `Jefe.estado` se respeta en login y resolución de bodega.
- Seguridad: la cuenta demo se siembra con contraseña de prototipo y se hashea con bcrypt en `ensure_schema()`. No se copiaron `/auth/demo-admin`, cookies/CSRF ni pagos del checkout de referencia.
- **Estado:** código y pruebas escritos; **no ejecutados en este entorno**. Falta validar el `403` entre admins, la desactivación y el bloqueo de productos de empleados contra una base desechable, además de la revisión visual en escritorio y móvil.

## Validación del shell móvil y favicon (ADR-009)

- Estática de contrato: `tests/test_web_shell_contract.py` comprueba en `operations-web`, `customer-web` y `admin-web` el `<link rel="icon">` a `/favicon.png`, la existencia y firma PNG de `public/favicon.png`, el botón de hamburguesa con `aria-haspopup`/`aria-expanded`, el panel `role="menu"` que sustituye a la barra inferior, la lista completa de secciones por rol y la escala móvil `1.55` con piso de `9px × escala`.
- Documentación: el mismo test detecta contradicciones conocidas (modo demo como fallback, `customer-web` ausente, ADR-009 fuera del índice) para que los cinco README y las specs no queden desincronizados del código.
- Cobertura de aplicaciones: el archivo revisa `backend` (`/customer/payment-methods`) y `database` (esquema de compras vigente), además de los tres frentends y el compose.
- **Estado:** pruebas estáticas escritas; **no ejecutadas en este entorno**. Falta revisión visual en dispositivo o emulador, comprobación de foco/teclado en el panel y ejecución de `npm run build` en las tres apps.

Pendiente: ejecutar `pytest` y `npm run build` en este entorno (la shell no pudo iniciarse y aquí no están `apps/backend/.venv`, `apps/operations-web/node_modules`, `apps/customer-web/node_modules` ni `apps/admin-web/node_modules`), validar una respuesta real con `GEMINI_API_KEY` para recomendaciones y para `Foto`/`Voz`, validar un EAN real/sintético en `Código` contra Open Food Facts, verificar la precisión real del dictado de precio/fecha/dígitos, verificar la cuota de multimedia y la disponibilidad de cada modelo autorizado (incluido un `503` por alta demanda), comprobar la persistencia de categorías con la base real, verificar la coherencia de las tres compras demo y su stock descontado, verificar el login admin, la autoprotección entre admins y la desactivación lógica con la base real, revisar el menú desplegable móvil y su legibilidad en dispositivo, definir criterios de precisión/utilidad (el historial disponible es solo sintético, no evidencia real), estrategia E2E, seguridad, usabilidad, datos de prueba y criterios de salida.
