# Plan técnico — REG-IA

**Estado:** Aprobado para el prototipo. Implementado en código, incluidos los cinco cambios de decisión de ADR-005. **Pendiente:** validación real de `Foto`/`Voz` con Gemini, de `Código` con Open Food Facts, ejecución de `pytest` y `npm run build`, y verificación de la precisión del dictado.

## Enfoque propuesto

Un adaptador en el backend recibe multimedia en base64, valida el modo y el archivo y devuelve un borrador saneado. `Foto`/`Voz` usan la Interactions API de ADR-004 con salida JSON estructurada; el prompt de `Voz` pide transcribir los ocho campos dictados y recibe la lista persistida de categorías. `Código` no llama a Gemini: toma los dígitos ya procesados por el navegador y consulta Open Food Facts. El frontend guarda el borrador en un hook compartido por **Registrar** y el modal de producto, y lo pasa a un `ProductForm` controlado. El guardado real sigue siendo `POST /products`. Para `Foto`/`Voz`, el backend publica una allowlist de modelos en `GET /ai/models` y valida el `modelo` recibido antes de construir la solicitud; el navegador solo envía un id autorizado y nunca la clave.

El catálogo de categorías se persiste aparte: `Categoria` con nombre primario y fecha de creación; `Producto.categoria` conserva el nombre de una sola categoría (relación lógica, no FK física). El selector de categoría crea categorías nuevas mediante `POST /categories`; el alta/edición de producto reutiliza o crea la categoría con `ensure_category`.

## Componentes afectados

| Capa | Archivo | Cambio |
|---|---|---|
| Configuración | `apps/backend/config.py`, `.env.example`, `docker-compose.yml` | `GEMINI_MODEL`, `GEMINI_ALLOWED_MODELS` opcional con default de dos modelos y `GEMINI_API_URL` compartida. |
| Adaptador de registro | `apps/backend/registration_ai.py` | Modos, validación de media, prompt/esquema de `voice` con ocho campos, consulta a Open Food Facts para `Código`, saneamiento con categorías de la base y `CATEGORIAS` como base/fallback con las mismas nueve categorías del seed/UI. `ICONOS` en paridad con el frontend. `resolve_model()` aplica la allowlist y `_request_body` usa el modelo resuelto. |
| API | `apps/backend/routers/registration.py` | `GET /ai/models` con ids autorizados y `POST /products/extract`, autenticado, sin escrituras; pasa `list_categories(conn)` y `modelo` a `extract_product_draft(...)`. |
| Categorías | `apps/backend/routers/categories.py` | `GET /categories` y `POST /categories` autenticados. |
| Esquema y arranque | `apps/database/database.sql`, `apps/database/seed.sql`, `apps/backend/database.py`, `apps/backend/main.py` | Tabla `Categoria`, nueve categorías base, `ensure_schema()` con migración deduplicada mediante `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))`, helpers `normalize_category`/`list_categories`/`ensure_category`, registro del router. |
| Productos | `apps/backend/routers/products.py` | `ensure_category` en `POST /products` y `PATCH /products/{id}`. |
| Cliente HTTP | `apps/operations-web/src/lib/api.js` | `extractProduct()`, `listAiModels()`, `listCategories()` y `createCategory()`. |
| Estado del borrador | `apps/operations-web/src/features/products/useProductDraft.js` | Estado compartido, merge del borrador, modelo seleccionado y mensajes de carga/error. |
| Capturas y selector | `apps/operations-web/src/features/products/ProductModal.jsx` | `PhotoCapture`, `BarcodeCapture` con botón cámara/imagen alterno, `VoiceCapture`, `PRODUCT_EMOJIS` con 124 emojis/keywords y `CategoryPicker` estilo Notion. |
| Carga inicial | `apps/operations-web/src/App.jsx` | `Promise.all` inicial para categorías y modelos; `addCategory` actualiza el estado y ambos se pasan a `RegisterPage` y `ProductModal`. |
| Página | `apps/operations-web/src/features/register/RegisterPage.jsx` | Conecta capturas con el hook y muestra estado de IA. |
| Formulario | `ProductModal.jsx` (`ProductForm`) | Controlado, editable y conectado al selector de categorías en texto/foto/código/voz. |
| Guardado | `apps/operations-web/src/App.jsx` | `addProduct(payload)` recibe el objeto del formulario. |
| Selector de modelo | `apps/operations-web/src/features/products/AiModelPicker.jsx` | Select controlado con los ids devueltos por el backend; aparece solo en `Foto`/`Voz` y no contiene clave ni URL. |
| Estilos | `apps/operations-web/src/styles.css` | Estado de análisis, error, grabación, selector expandible y selector de modelo. |
| Pruebas | `tests/test_registration_ai.py`, `tests/test_backend_api.py`, `tests/test_endpoint_usage.py` | Voz completa, categorías dinámicas, paridad de emojis, alternancia de cámara, persistencia estática y paridad de endpoints. |

## Contratos / interfaces

### `POST /products/extract`

- Autenticación: `Authorization: Bearer <token>`. Jefe y empleado.
- Solicitud:

```json
{
  "modo": "photo | barcode | voice",
  "data": "data:image/jpeg;base64,...",
  "mime_type": "image/jpeg",
  "codigo": "7750182003412",
  "duracion": 12
}
```

`mime_type` y `codigo` son opcionales; `duracion` solo aplica a `voice` y se expresa en segundos. `data` acepta dataURL o base64 puro.

- Respuesta `200` para `voice` con dictado completo:

```json
{
  "modo": "voice",
  "campos": {
    "nombre": "Yogurt natural",
    "icono": "🥛",
    "categoria": "Lácteos",
    "cantidad": 12,
    "unidad": "unidad",
    "precio_venta": 3.5,
    "fecha_vencimiento": "2026-12-15",
    "codigo_barras": "7750182003412"
  },
  "modelo": "Gemini",
  "mensaje": "Revisa y corrige los campos antes de guardar.",
  "aviso": "La asistencia solo propone datos revisables. No guarda productos, no crea movimientos ni modifica stock: nada se aplica hasta que confirmes el formulario."
}
```

Los campos no dictados se omiten; no se calculan valores ausentes.

- Respuesta `200` para `barcode`:

```json
{
  "modo": "barcode",
  "campos": {
    "nombre": "Yogurt natural",
    "icono": "🥛",
    "categoria": "Lácteos",
    "unidad": "litro",
    "codigo_barras": "7750182003412",
    "fuente": "https://world.openfoodfacts.org/product/7750182003412"
  },
  "modelo": "Open Food Facts",
  "mensaje": "Datos obtenidos de Open Food Facts; revisa y corrige antes de guardar.",
  "aviso": "La asistencia solo propone datos revisables. No guarda productos, no crea movimientos ni modifica stock: nada se aplica hasta que confirmes el formulario."
}
```

- `400`: modo, MIME, base64 o tamaño inválidos; `barcode` sin imagen o sin dígitos legibles.
- `401`: sin token o token inválido.
- `503`: Gemini no configurada/no disponible en `Foto`/`Voz`, u Open Food Facts no disponible en `Código`.

Si el EAN no existe en Open Food Facts, la respuesta es `200` con `campos: {codigo_barras: "..."}` y el mensaje “No se encontró en la base de datos. Regístralo manualmente.”

### Categorías

- `GET /categories`: devuelve los nombres persistidos, autenticado.
- `POST /categories`: crea una categoría si no existe; reutiliza la existente sin distinguir mayúsculas/minúsculas y trunca el nombre a 100 caracteres. El selector selecciona la categoría creada.
- `normalize_category`/`ensure_category`: saneamiento y reutilización compartidos con `POST /products` y `PATCH /products/{id}`.

### Llamada a Gemini

`POST https://generativelanguage.googleapis.com/v1beta/interactions` con `x-goog-api-key`, solo para `Foto`/`Voz`. `v1beta` es obligatorio porque `v1` rechaza los bloques `image`/`audio` inline con `400`. El `input` es un arreglo con texto y el bloque `image` o `audio` (`data` + `mime_type`). `response_format` usa `mime_type: application/json` y un esquema cerrado de ocho campos para `voice`. `store: false`. La salida se lee desde `output_text` o `steps[].content[].text`. El prompt de `voice` recibe la lista de categorías; precio y fecha se transcriben solo si se dictan, con fecha ISO `AAAA-MM-DD`, sin estimar vida útil.

### Consulta de Open Food Facts

`GET {OPEN_FOOD_FACTS_API_URL}/{digitos}?fields=...` con `User-Agent` y `Accept: application/json`. No requiere key. Si `status != 1` o el producto no trae datos, se devuelve el mensaje de registro manual. La fuente se restringe a HTTP(S) y se muestra como referencia. No se envían bodega, correos ni stock.

## Datos y persistencia

La extracción no inserta, actualiza ni borra productos, lotes ni movimientos. El borrador se mantiene en memoria del navegador. Solo el envío del formulario existente crea `Producto` y `ProductosBodega`. `store: false` evita que el proveedor retenga la interacción.

La creación explícita de categoría desde el selector sí persiste en `Categoria`; es una acción del usuario, no de la IA. `ensure_schema()` crea la tabla si falta, migra nombres existentes de `Producto` con `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))`, deduplicando por clave insensible a mayúsculas/minúsculas, y siembra nueve categorías base. `Producto.categoria` sigue siendo `VARCHAR(100)` con el nombre de una sola categoría: relación lógica, no FK física.

## Seguridad y permisos

- La clave se inyecta solo al contenedor `backend` desde `.env` ignorado por Git.
- El frontend llama al backend; nunca a Google. Prueba estática sobre `src/`.
- No se envían correos, nombres de empleado, bodega ni stock del inventario; solo multimedia, prompt cerrado y la lista de categorías.
- Validación de MIME, tamaño y base64 antes de reenviar; error `503` con detalle redactado.
- `Código` consulta una base pública por dígitos; la fuente devuelta se limita a HTTP(S) y se muestra como referencia, no como verdad confirmada. No se usa *Search grounding* por no estar en el plan gratuito.
- `Voz` transcribe, no estima. Si faltan precio o fecha en el audio, permanecen vacíos para que el usuario los ingrese.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Gemini transcribe mal precio, fecha o dígitos en `Voz` | Esquema cerrado, saneamiento, campos editables y confirmación del usuario. No se rellena lo no dictado; precisión pendiente de validar con grabaciones reales. |
| Gemini inventa un producto en `Foto`/`Voz` | Esquema cerrado, saneamiento y campos editables; el usuario confirma. |
| Se adivina un producto solo con los dígitos | `Código` no usa la memoria del modelo: consulta Open Food Facts y, si no hay coincidencia, pide registro manual. |
| Datos de Open Food Facts incompletos o viejos | Editables, etiquetados como preliminares y con fuente visible. Precio y vencimiento no se proponen en este modo. |
| Categorías duplicadas por capitalización | `normalize_category`/`ensure_category` reutilizan el nombre canónico y truncan a 100 caracteres. |
| Desbordamiento del selector de categorías | Buscador y opciones filtradas; el catálogo crece solo por creación explícita. |
| Falta de paridad de emojis entre capas | `PRODUCT_EMOJIS` e `ICONOS` se mantienen en paridad exacta con prueba automatizada. |
| Datos del tier gratuito usados para mejorar productos | Solo multimedia sintético o propio en pruebas; registrado en ADR-005. |
| Archivo demasiado grande o MIME falso | Validación estricta en backend antes de la llamada externa. |
| Navegador sin `MediaRecorder` o `BarcodeDetector` | Mensaje claro; alternativas manuales intactas. |
| Fuga de clave al cliente | Variable solo en backend y prueba estática. |
| Retención por el proveedor | `store: false`. |

## Decisiones requeridas

- **Confirmadas:** expansión de alcance; imagen para `Código`; consulta por dígitos en Open Food Facts; `Voz` transcribe todos los campos dictados sin estimar vida útil; precio/vencimiento manuales solo en `Foto` y `Código`; botón de cámara alterno; emojis amplios con paridad; categorías persistentes con una sola categoría por producto; campos revisables; datos de prueba sintéticos.
- **Pendientes:** precisión real del dictado con audio, cuota real de multimedia, modelo definitivo de producción y auditoría futura de EN-08.

## Validación técnica

- Pruebas unitarias del adaptador sin red: request por modo, saneamiento de ocho campos de voz, categorías dinámicas, paridad de emojis, alternancia de cámara, persistencia estática y errores redactados.
- Prueba estática de paridad entre rutas del backend y helpers de `api.js`, incluidas `GET/POST /categories`.
- Prueba HTTP: `400` con datos inválidos y verificación de no mutación de productos.
- Compilación del frontend con `npm run build`.
- Validación real con `GEMINI_API_KEY` en `Foto`/`Voz` y con un EAN propio/sintético en `Código`: **pendiente**; debe registrarse en `docs/06-quality/README.md`.
