# ADR-005: Registro asistido por foto, voz y código de barras con Gemini y Open Food Facts

**Estado:** Aceptado por el usuario el 2026-11-26 como expansión formal del alcance. La misma fecha amplió la decisión para que `Voz` transcriba todos los campos dictados, el botón del medio de `Código` alterne cámara/imagen, el selector de Ícono tenga más emojis con paridad y Categoría sea expandible y persistente. El 2026-11-26 también pidió un selector de modelo Gemini en la interfaz; se implementó con allowlist en el backend. Prototipo implementado. Hubo una prueba real con foto que devolvió `400` porque `v1` no acepta imágenes inline; el endpoint se cambió a `v1beta`. La prueba real de `Código` devolvió `429` por `google_search` en el plan gratuito; ese modo pasó a consultar Open Food Facts. Un intento posterior con `gemini-3.1-flash-lite` devolvió `503 service_unavailable` por alta demanda; se optó por esperar y reintentar y, a petición del usuario, exponer modelos autorizados. **Faltan una validación real exitosa**, ejecutar `pytest` y `npm run build`, y verificar la precisión del dictado.

**Fecha:** 2026-11-26

## Contexto

El alcance inicial excluía “registro automático por voz/fotografía” (constitución y `scope.md`). El usuario pidió integrar Gemini en la pantalla **Registrar** para que `Foto`, `Código` y `Voz` completaran automáticamente nombre, ícono, categoría, cantidad con unidad y precio/vencimiento cuando fuera posible, dejando la confirmación al usuario. Consultado formalmente, confirmó la expansión de alcance.

Tras el `429` de `google_search`, el usuario precisó que `Código` debía consultar una base pública de códigos y pedir registro manual si no encontraba el producto. En ese momento, precio y vencimiento quedaron manuales en los tres modos porque la fuente pública no los expone. **Esa redacción fue sustituida por una decisión posterior del usuario**: en `Voz`, precio, vencimiento y código de barras se toman del dictado, nunca se estiman; en `Foto` y `Código` siguen manuales.

También se pidió:

- Que el botón del medio en `Código` alternara entre tomar la foto del código enfocado y volver a encender la cámara.
- Que `Voz` transcribiera **todos** los campos dictados por Gemini, incluidos `precio_venta`, `fecha_vencimiento` y `codigo_barras` cuando se dictan dígitos, sin estimar vida útil.
- Más emojis en el selector de Ícono de Foto/Código/Texto/Voz, con paridad frontend/backend.
- Una Categoría expandible estilo Notion con «Agregar nueva categoría», persistida en la base, con una sola categoría por producto.

La documentación oficial de Gemini consultada indica que `gemini-3.1-flash-lite` acepta texto, imagen, audio y PDF y ofrece *structured outputs*. `v1` rechazó imágenes inline con `400`, por lo que el endpoint compartido se cambió a `v1beta/interactions`. Para `Código` se habilitó inicialmente `google_search`, pero una prueba real devolvió `429 too_many_requests`: *Search grounding* no está disponible en el plan gratuito de Gemini 3.1 Flash-Lite. Por decisión del usuario, `Código` consulta la API pública de Open Food Facts por EAN/UPC y Gemini no adivina el producto a partir de los dígitos. Los archivos en línea limitan la solicitud a 20 MB; este prototipo impone límites menores (8 MB por archivo).

## Decisión

- Agregar **REG-IA** como expansión de CU-02, con el endpoint autenticado `POST /products/extract`. La extracción no crea ni modifica productos: devuelve un borrador saneado.
- Permitir el endpoint a jefe y empleado (RN-02). No se envían datos de otras bodegas ni inventario.
- Enviar multimedia como `data:` base64; el backend decodifica, valida MIME y tamaño, y reenvía `Foto`/`Voz` a `v1beta/interactions` con `x-goog-api-key`, JSON Schema y `store: false`. La clave nunca sale del backend. En `Código` la imagen se valida igual, pero la resolución se hace con Open Food Facts.
- Modos y campos permitidos:

  | Modo | Fuente de datos | Campos que puede proponer | Campos manuales / condición |
  |---|---|---|---|
  | `photo` | Gemini + imagen del producto/etiqueta | `nombre`, `icono`, `categoria`, `cantidad`, `unidad` (stock inicial) | `precio_venta`, `fecha_vencimiento` y código siguen manuales. |
  | `voice` | Gemini + dictado grabado en el navegador | Los cinco campos anteriores más `precio_venta`, `fecha_vencimiento` y `codigo_barras` **si se dictan explícitamente** | Los no dictados quedan para completar en el formulario. Precio y fecha son transcripción, no estimación; la fecha se expresa ISO `AAAA-MM-DD`. No se deduce vida útil. |
  | `barcode` | Open Food Facts + dígitos procesados de la imagen | `nombre`, `icono`, `categoria`, `unidad`, `codigo_barras` y `fuente` cuando existan | `cantidad`, `precio_venta` y `fecha_vencimiento` siguen manuales: Open Food Facts no expone precio ni vencimiento en este corte. |

- El prompt y el esquema JSON de `voice` incluyen los ocho campos indicados. El prompt recibe la lista persistida de categorías; `CATEGORIAS` queda como base/fallback con las mismas nueve categorías del seed/UI y el saneamiento acepta categorías de la base.
- La salida se sanea en el backend: categorías reutilizables de la lista persistida, unidades y iconos de listas cerradas, cantidad entera positiva, precio positivo, fecha ISO válida, código EAN/UPC de 8 a 14 dígitos y fuente HTTP(S) opcional. Lo inválido se omite.
- `Categoria` se crea en `apps/database/database.sql` con `nombre VARCHAR(100) PRIMARY KEY` y `fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP`. `Producto.categoria` sigue `VARCHAR(100)` y guarda el nombre de una sola categoría: relación lógica, no FK física. `seed.sql` siembra nueve categorías base. `ensure_schema()` crea la tabla si falta, migra nombres existentes desde `Producto` con `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))`, deduplicando por clave insensible a mayúsculas/minúsculas, y siembra las base. `normalize_category`, `list_categories` y `ensure_category` reutilizan categorías sin distinguir mayúsculas/minúsculas, crean la que falte y truncan a 100 caracteres. `GET /categories` y `POST /categories` están autenticados; `POST /products` y `PATCH /products/{id}` llaman a `ensure_category`. Esto es un detalle de implementación de EN-03, no una nueva entidad de negocio (RN-14, RF-29).
- `PRODUCT_EMOJIS` se amplió a 124 emojis con keywords y `ICONOS` del backend mantiene paridad exacta. El selector de Ícono está disponible en Foto/Código/Texto/Voz (RF-30).
- En `BarcodeCapture`, el botón del medio captura un frame cuando la cámara está lista y, si está apagada, llama a `restartCamera()`. Intenta `BarcodeDetector` sobre el canvas capturado y alterna la etiqueta entre «Usar imagen del código» y «Encender cámara». «Subir imagen» y «Leer dígitos» siguen disponibles.
- El selector de Categoría es expandible estilo Notion: buscador, opciones filtradas y «Agregar nueva categoría «término»». Llama a `POST /categories` y selecciona la creada. Está conectado en todos los modos de registro.
- La interfaz precarga el formulario con lo devuelto; el usuario puede corregir cualquier campo y solo al pulsar **Guardar en inventario** llama al `POST /products` existente. Crear una categoría persiste solo el catálogo, no un producto ni un movimiento. La IA no aprueba, guarda ni cambia stock por sí sola (RN-08).
- El selector de modelo aparece solo en `Foto` y `Voz`. `GET /ai/models` devuelve `default`, `modelos` con `{id, label, activo}` y una nota; el frontend envía `modelo` en `POST /products/extract`. `config.py` mantiene `GEMINI_ALLOWED_MODELS` (por defecto `gemini-3.1-flash-lite,gemini-3.5-flash-lite`, siempre incluyendo `GEMINI_MODEL`); `resolve_model()` acepta vacío como default y rechaza cualquier otro id con `400`. La clave y la URL del proveedor no llegan al bundle (RF-34, RN-17).
- Límites del prototipo: imagen decodificada ≤ 8 MB, audio decodificado ≤ 8 MB y audio ≤ 60 s. Si el proveedor falta o falla, se responde `503` y el formulario sigue utilizable en modo manual.

## Consecuencias

### Positivas

- El registro asistido deja de ser una simulación: `Foto` y `Voz` envían multimedia real a Gemini; `Código` consulta una base pública real.
- `Voz` aprovecha el dictado para completar precio, vencimiento y código sin convertir una sugerencia en una estimación de vida útil.
- La decisión y la escritura siguen siendo del usuario; no se introduce compra, movimiento ni precio automático.
- El catálogo de categorías crece con el uso y se reutiliza de forma consistente; no se agrega una entidad de negocio nueva.
- El selector de íconos y el botón de cámara alterno reducen pasos manuales sin quitar las alternativas de subir imagen o leer dígitos.
- Un solo endpoint y un único adaptador reducen la superficie de clave y facilitan pruebas sin red.
- El selector permite probar otro modelo autorizado sin editar variables ni recrear el backend cuando el default esté saturado.

### Negativas / riesgos

- La transcripción de audio puede equivocarse en precios, fechas o dígitos. Por eso son campos editables y la validación real con grabaciones queda pendiente; no se estima contenido ausente.
- Open Food Facts es colaborativa y no cubre todos los productos; si el EAN no está, el formulario queda con el código y se pide registro manual. No se inventa un producto.
- Los datos de Open Food Facts pueden estar incompletos o desactualizados; son sugerencias editables con fuente visible. No expone precio ni vencimiento.
- El tier gratuito de Gemini puede usar los archivos enviados para mejorar productos: solo se permiten pruebas sintéticas o propias hasta decidir un tier de pago.
- La grabación depende de `MediaRecorder` y permisos del navegador; si no están disponibles, el modo manual sigue funcionando.
- La cámara depende de `getUserMedia`/`BarcodeDetector`; si faltan, «Subir imagen» y «Leer dígitos» siguen disponibles.
- La cuota real para multimedia de Gemini sigue pendiente de verificación; *Search grounding* quedó fuera del diseño al eliminarlo de `Código`.
- El selector no garantiza disponibilidad: ambos modelos autorizados pueden devolver `503` simultáneamente por alta demanda. Cambiar de modelo no debe interpretarse como evidencia de precisión ni como aprobación automática.

## Alternativas consideradas

- **Precio y vencimiento manuales en los tres modos:** fue la decisión original, pero el usuario la sustituyó el 2026-11-26 para `Voz`. Se conserva solo para `Foto` y `Código`.
- **Estimar vencimiento a partir de la imagen o del tipo de producto:** descartado; sigue fuera del MVP y no se deduce vida útil.
- **Que Gemini adivine el producto solo con los dígitos:** descartado; `Código` consulta Open Food Facts y pide registro manual si no hay coincidencia.
- **Catálogo local de códigos de barras:** descartado por ahora; no existe esa tabla en el MVP y ampliaría el modelo de datos.
- **Mantener `google_search`:** descartado para el prototipo gratuito; la prueba real devolvió `429` y la documentación oficial no lo incluye en el plan gratuito.
- **Lista de categorías fija en el frontend:** sustituida por el catálogo persistente; la lista base sigue como fallback.
- **Lista cerrada de emojis o un solo botón de cámara:** sustituidas por el selector amplio con paridad y la alternancia cámara/imagen.
- **Bloquear campos sugeridos:** descartado; el usuario pidió poder corregirlos.
- **Texto libre para el modelo en el navegador:** descartado; permitiría ids de pago o inexistentes y sacaría el control de la cuota del backend. Se eligió una allowlist servida por `GET /ai/models`.
- **Reintento automático ante `503`:** descartado por ahora; el usuario eligió esperar y reintentar manualmente para no consumir cuota extra sin validación.
- **Subir archivos a Files API:** no necesario en este corte; multimedia pequeña se envía en línea y `store: false` evita retener la interacción.

## Trazabilidad

CU-02, CU-04; RF-25…RF-30, RF-34; RN-02, RN-03, RN-08, RN-12, RN-13, RN-14, RN-17; EN-03, EN-08; [REG-IA](../../05-specifications/registro-asistido-ia/spec.md); ADR-004 (mismo proveedor y modelo para `Foto`/`Voz`); Open Food Facts API (fuente pública para `Código`).
