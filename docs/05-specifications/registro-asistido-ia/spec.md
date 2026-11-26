# REG-IA — Registro asistido por foto, código de barras y voz

**Estado:** Aprobado para el prototipo por el usuario; decisión ampliada el 2026-11-26 para transcripción de voz completa, cámara alterna, emojis amplios, categorías persistentes y selector de modelo Gemini con allowlist. Implementado en código. **Pendiente:** validación real de `Foto`/`Voz` con Gemini, validación de `Código` con Open Food Facts, ejecución de `pytest` y `npm run build`, y verificación de la precisión del dictado.

## Identificador y trazabilidad

`REG-IA` es un identificador técnico incremental que amplía **CU-02** (gestionar bodega y catálogo) y se apoya en **CU-04** (entradas). La expansión de alcance y sus cambios posteriores quedaron registrados en **ADR-005**.

## Problema y objetivo

**Confirmado:** registrar productos es una operación frecuente y las entrevistas exploratorias identificaron simplicidad y rapidez como necesidades. No demuestran que la asistencia reduzca pérdidas ni que sea precisa.

**Objetivo del incremento:** que `Foto` y `Voz` propongan o transcriban datos iniciales mediante Gemini y que `Código` los obtenga de Open Food Facts, con el usuario revisando y confirmando antes de guardar.

## Alcance incluido / excluido

### Incluido

- Captura real de foto desde cámara/galería y envío de la imagen en base64 al backend.
- Escaneo o foto del código de barras; los dígitos procesados se consultan directamente en la API pública de Open Food Facts.
- En `Código`, botón del medio que alterna entre capturar la imagen enfocada y volver a encender la cámara; intenta `BarcodeDetector` sobre el canvas capturado y mantiene «Subir imagen» y «Leer dígitos».
- Grabación real de voz con `MediaRecorder` y envío del audio en base64 al backend.
- `Voz` transcribe los ocho campos dictados por Gemini: nombre, ícono, categoría, cantidad, unidad, `precio_venta`, `fecha_vencimiento` y `codigo_barras` si se dictan dígitos. Precio y fecha se transcriben solo si se dicen explícitamente; la fecha se expresa en ISO `AAAA-MM-DD`; la IA no estima vida útil.
- Selector de Ícono amplio (124 emojis con keywords) con paridad exacta entre frontend y backend en Foto/Código/Texto/Voz.
- Selector de Categoría expandible estilo Notion: buscador, opciones filtradas, «Agregar nueva categoría» y persistencia en la base. Cada producto guarda una sola categoría por nombre.
- Respuesta estructurada y saneada con: nombre, ícono, categoría, unidad, fuente y, según el modo, cantidad, precio, vencimiento y código.
- Formulario controlado y editable: el usuario puede corregir todo antes de `POST /products`.
- Mensaje de estado durante el análisis y mensaje de error controlado sin perder el formulario.
- Catálogo persistente de categorías con `Categoria(nombre VARCHAR(100) PRIMARY KEY, fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)`, nueve categorías base, migración de nombres existentes y endpoints `GET /categories` y `POST /categories` autenticados.

### Excluido

- Guardar, aprobar o publicar el producto desde la IA; solo el usuario confirma con el formulario existente.
- Crear movimientos de inventario, compras, órdenes ni promociones desde esta funcionalidad.
- Persistir el borrador de IA en EN-08; vive solo en la sesión del navegador. La persistencia de categoría es distinta: guarda el catálogo, no un borrador ni un producto.
- Una nueva entidad de negocio para categoría: `Categoria` es un detalle de implementación de EN-03 (RN-14).
- Catálogo propio de códigos de barras, proveedores, pagos, facturación, entregas, contabilidad ni vista pública.
- Estimación de vida útil por IA. En `Voz`, la fecha vencimiento es transcripción del dictado explícito; en `Foto` y `Código` se ingresa manualmente.
- Datos reales de clientes en las pruebas del tier gratuito.

## Actores y permisos

| Actor | Permiso |
|---|---|
| Jefe (AN-02) | Puede usar los tres modos; hereda operaciones del empleado según RN-02. Puede crear categorías desde el selector. |
| Empleado (AN-03) | Puede usar los tres modos dentro de su bodega; la extracción no escribe datos. Puede crear categorías desde el selector. |
| Gemini | Solo propone/transcribe campos en `Foto`/`Voz`. No aprueba, no guarda, no modifica stock (RN-08). |
| Open Food Facts | Fuente pública de solo lectura para `Código`. No recibe inventario ni datos personales. |

## Precondiciones y postcondiciones

**Precondiciones:** sesión válida; permiso de cámara/micrófono para los modos que lo requieren; `GEMINI_API_KEY` configurada en el backend solo para `Foto`/`Voz`. En `Código`, el navegador debe entregar dígitos legibles mediante `BarcodeDetector` sobre el canvas capturado o el usuario debe escribirlos; también puede subir una imagen. El frontend carga las categorías disponibles antes de mostrar el selector.

**Postcondiciones de la extracción:** no se inserta, actualiza ni elimina ningún producto, lote ni movimiento; se devuelve un borrador saneado. La postcondición de registro se produce solo cuando el usuario envía explícitamente `POST /products` con los valores que revisó. La creación explícita de categoría inserta solo una fila en `Categoria` y la reutiliza por nombre sin distinguir mayúsculas/minúsculas.

## Flujo principal

1. El usuario abre **Registrar** o el modal de producto y elige texto, `Foto`, `Código` o `Voz`.
2. La aplicación obtiene el catálogo persistido de categorías y los modelos autorizados (`GET /ai/models`) y pasa ambos al formulario y al prompt de voz.
3. Captura la imagen o el audio; el navegador convierte el archivo a `data:` base64.
4. El frontend llama a `POST /products/extract` con `modo`, `data` y, si aplica, `mime_type`, `codigo`, `duracion` (segundos, solo para voz) y `modelo` elegido en `Foto`/`Voz`.
5. El backend valida autenticación, tipo de archivo y tamaño. En `photo`/`voice` llama a Gemini con `store: false` y con la lista de categorías; en `barcode` consulta Open Food Facts con los dígitos recibidos.
6. El backend sanea la salida y devuelve `campos`, `modo`, `modelo` (proveedor usado), `mensaje` y `aviso`.
7. La UI precarga el formulario. `Voz` puede llegar con precio, vencimiento y código dictados; `Foto` no los propone y en `Código` siguen manuales. El usuario puede crear una categoría nueva desde el selector.
8. El usuario corrige lo necesario y pulsa **Guardar en inventario**; recién allí se crea el producto.

## Alternativas y excepciones

| Situación | Comportamiento |
|---|---|
| Sin permiso de cámara o micrófono | Se informa; el usuario puede usar `Buscar`, `Texto`, «Subir imagen», «Leer dígitos» o completar manualmente. |
| `MediaRecorder` no soportado | El botón de voz informa que el navegador no permite grabar; no se envía audio falso. |
| `BarcodeDetector` no disponible o cámara apagada | El botón del medio puede encender/reiniciar la cámara; el usuario puede escribir dígitos o subir una imagen. |
| Modo desconocido, MIME no permitido, base64 inválido o archivo demasiado grande | `400`; el formulario permanece vacío y utilizable. |
| Falta `GEMINI_API_KEY` o Gemini falla en `Foto`/`Voz` | `503` con detalle redactado; no se muta inventario. |
| Modelo enviado fuera de la allowlist | `400`; el formulario sigue utilizable y no se llama al proveedor. |
| Modelo autorizado saturado | Puede devolver `503 service_unavailable`; el usuario puede esperar, reintentar o elegir otro modelo autorizado. No se aplica nada automáticamente. |
| Open Food Facts no responde en `Código` | `503` con mensaje para registrar manualmente; no se muta inventario. |
| Gemini no identifica el producto o devuelve solo campos inválidos | `200` con `campos: {}` y mensaje indicando que complete manualmente. |
| Código sin imagen o sin dígitos legibles | `400`; el usuario debe capturar/subir la imagen o escribir el código. |
| EAN no existe en Open Food Facts | `200` con `codigo_barras` y el mensaje “No se encontró en la base de datos. Regístralo manualmente.” |
| Categoría no persistida, unidad, icono, fecha, precio o cantidad fuera de dominio | Se omite ese campo durante el saneamiento. Se aceptan categorías de la base además de la base/fallback `CATEGORIAS`, que tiene las mismas nueve categorías del seed/UI. |
| El usuario crea una categoría ya existente con distinta capitalización | `ensure_category` reutiliza el nombre canónico y no crea duplicado. |

## Reglas de negocio

- **RN-02:** el jefe puede operar como empleado; el empleado solo ve su bodega. La extracción no consulta ni envía inventario de otra bodega.
- **RN-03:** la cantidad inicial que se guarde debe ser positiva; la validación final sigue en `POST /products`.
- **RN-08:** la IA es apoyo; nunca aprueba ni escribe. Guardar es una acción explícita del usuario.
- **RN-12:** política de campos por modo (tabla en ADR-005). `cantidad` se propone en `photo` y `voice` como stock inicial; en `barcode` la ingresa el usuario. `Voz` incluye todos los campos dictados.
- **RN-13:** en `Voz`, `precio_venta` y `fecha_vencimiento` provienen de la transcripción del dictado explícito (ISO `AAAA-MM-DD`), no de estimación de vida útil; siempre son editables. En `Foto` son manuales. En `Código`, Open Food Facts no expone esos campos y siguen manuales.
- **RN-14:** catálogo persistente de categorías; una sola categoría por producto; creación desde el registro y reutilización insensible a mayúsculas/minúsculas.
- **RN-17:** `Foto`/`Voz` solo usan modelos de la allowlist del backend; `GET /ai/models` publica los ids autorizados y el navegador no puede enviar otro ni la clave.
- El esquema JSON y el saneamiento se aplican por separado; la validación del esquema de salida no se considera suficiente.

## Datos y entidades

- **EN-03:** `nombre`, `icono`, `categoria`, `unidad_medida`, `precio_venta`, `fecha_vencimiento` y stock inicial se mapean al payload existente de `POST /products`. `categoria` guarda el nombre de una sola categoría del catálogo `Categoria`; relación lógica, no FK física.
- **EN-04:** el vencimiento sugerido o dictado es informativo; no crea lote ni movimiento.
- **EN-08:** no se persiste sugerencia ni decisión en este corte.
- `Categoria` se siembra con nueve nombres base; `ensure_schema()` crea la tabla si falta y migra categorías existentes desde `Producto` con `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))`, deduplicando por clave insensible a mayúsculas/minúsculas. `normalize_category`, `list_categories` y `ensure_category` reutilizan o crean según corresponda y truncan a 100 caracteres.
- Los campos se envían al proveedor solo dentro del archivo multimedia, del prompt y de la lista persistida de categorías; no se envían correos, nombres de empleados ni stock de la bodega.

## Criterios de aceptación

| Criterio | Estado en el prototipo | Validación pendiente |
|---|---|---|
| `Foto` envía una imagen real y completa nombre, ícono, categoría, cantidad y unidad; precio, vencimiento y código quedan manuales. | Implementado | Prueba real con Gemini. |
| `Voz` graba audio real y transcribe los ocho campos dictados, con precio/fecha solo explícitos e ISO `AAAA-MM-DD`, sin estimar vida útil. | Implementado | Prueba real con audio y revisión de precisión. |
| `Código` envía imagen y dígitos, consulta Open Food Facts y propone solo campos disponibles; si no hay coincidencia, muestra el mensaje de registro manual. Cantidad, precio y vencimiento siguen manuales. | Implementado | Prueba real con EAN propio/sintético. |
| El botón del medio de `Código` alterna foto/cámara; «Subir imagen» y «Leer dígitos» siguen disponibles. | Implementado | Prueba en navegador con y sin permiso de cámara. |
| El selector de Ícono ofrece 124 emojis con keywords y hay paridad frontend/backend. | Implementado | Verificación automatizada y revisión visual. |
| El selector de Categoría permite crear y reutilizar categorías persistidas; una sola categoría por producto. | Implementado | Verificación de migración y reutilización con la base real. |
| Todo lo propuesto o dictado es editable y no se guarda hasta que el usuario pulsa **Guardar en inventario**. | Implementado | Prueba funcional. |
| Sin clave o con proveedor caído, la respuesta es `503`, el detalle no filtra la clave y el formulario manual sigue funcionando. | Implementado | Prueba con configuración real; comprobar los dos modelos autorizados por separado. |
| `Foto`/`Voz` pueden elegir modelos autorizados; un id arbitrario se rechaza con `400` y la clave no aparece en el frontend. | Implementado | `pytest`, `npm run build` y prueba con el allowlist real. |
| La extracción no crea ni modifica productos, movimientos ni stock. | Implementado | `pytest` y verificación de no mutación. |
| El frontend no contiene `GEMINI_API_KEY` ni llama directamente a Google. | Implementado | Prueba estática. |
| Las pruebas unitarias, estáticas y de paridad pasan con `apps/backend/.venv`; compila `apps/operations-web` con `npm run build`. | No verificado en este entorno | Ejecutar y registrar en `docs/06-quality/README.md`. |

## Escenarios de prueba

| Escenario | Resultado esperado |
|---|---|
| Foto sintética de una etiqueta | Borrador con nombre, ícono, categoría, cantidad y unidad; sin precio, vencimiento ni código propuestos. |
| Audio sintético con dictado de ocho campos | Borrador con los ocho campos; precio y fecha solo si se dictaron; sin estimación de vencimiento. |
| Audio sin precio ni fecha | Esos campos quedan vacíos para completar manualmente; se transcriben nombre/cantidad u otros campos dictados. |
| Dictado de dígitos de código de barras | `codigo_barras` se incluye en el borrador de voz; no se consulta Open Food Facts desde `Voz`. |
| Imagen de código de barras con dígitos legibles | Se consulta Open Food Facts; se sanean nombre, ícono, categoría, unidad, código y fuente; cantidad, precio y vencimiento vacíos. |
| Botón del medio con cámara lista | Captura el frame enfocado e intenta `BarcodeDetector`; etiqueta «Usar imagen del código». |
| Botón del medio con cámara apagada | Reinicia la cámara; etiqueta «Encender cámara» hasta que haya frame listo. |
| Empleado autenticado usa el endpoint | `200`; sin escritura de producto, lote ni movimiento. |
| MIME `application/pdf` en `photo` | `400`. |
| Base64 malformado o > 8 MB | `400`. |
| Proveedor devuelve categoría no persistida | Para `Foto`/`Voz` se omiten las fuera del dominio; las categorías de la base son aceptadas. |
| Usuario crea «Agregar nueva categoría «Congelados»» | `POST /categories` persiste el nombre; el selector lo marca como seleccionado y se reutiliza sin duplicar por capitalización. |
| EAN ausente en Open Food Facts | `200` con el mensaje “No se encontró en la base de datos. Regístralo manualmente.” y solo el código; sin mutación. |
| Sin `GEMINI_API_KEY` en `Foto`/`Voz` | `503`; sin mutación. `Código` no depende de esa clave. |
| Selector en `Foto`/`Voz` con modelo alterno autorizado | El cuerpo enviado a Gemini usa ese `model` y la respuesta informa el mismo modelo; el formulario sigue revisable. |
| Selector con id fuera de la allowlist | `400` con «Modelo de IA no permitido»; sin llamada al proveedor ni mutación. |

## Dependencias

- Backend FastAPI existente, token HMAC y `POST /products`.
- `GEMINI_API_KEY`, `GEMINI_MODEL` y `GEMINI_API_URL` definidos en ADR-004 para `Foto`/`Voz`; `GEMINI_ALLOWED_MODELS` es opcional y por defecto incluye `gemini-3.1-flash-lite` y `gemini-3.5-flash-lite` más el `GEMINI_MODEL` configurado (RF-34, RN-17).
- Open Food Facts API v2 expuesta por `OPEN_FOOD_FACTS_API_URL`, sin key y con User-Agent identificable; el límite público es 15 consultas/minuto por IP.
- Interactions API `v1beta` (necesaria para imagen/audio inline; `v1` devolvió `400` en la prueba real) y `response_format` con JSON Schema para `Foto`/`Voz`. No se usa `google_search`.
- Navegador con `getUserMedia`, `MediaRecorder` y, para `Código`, `BarcodeDetector`; hay alternativa manual si faltan.
- Tabla `Categoria` y router de categorías autenticado, con `listCategories`/`createCategory` en `api.js`.
- Cuota real del tier gratuito para multimedia: **pendiente** de verificar. *Search grounding* quedó fuera del corte.

## Preguntas abiertas

1. ¿Cuál es la precisión real del dictado de precio, fecha y dígitos en audio con ruido, acentos o referencias relativas? El usuario debe corregir antes de guardar.
2. ¿El tier gratuito de la cuenta cubre la cuota de multimedia usada por `Foto`/`Voz`?
3. ¿Se verificará automáticamente el contenido de la fuente pública o del dictado antes de mostrarlo? Hoy son borradores revisables.
4. ¿Se migrará a Files API o a un tier de pago si aumenta el tamaño de las imágenes?
5. ¿Se desea auditoría de las sugerencias aceptadas en EN-08? Queda fuera de este corte.

## Trazabilidad

| Caso | Requisitos | Reglas | Entidades | Decisión | Código / pruebas |
|---|---|---|---|---|---|
| CU-02, CU-04 | RF-25…RF-30, RF-34 | RN-02, RN-03, RN-08, RN-12, RN-13, RN-14, RN-17 | EN-03, EN-04, EN-08 | ADR-005 | `apps/backend/config.py`, `apps/backend/registration_ai.py`, `apps/backend/routers/registration.py`, `apps/backend/routers/categories.py`, `apps/backend/database.py`, `apps/database/database.sql`, `apps/database/seed.sql`, `docker-compose.yml`, `apps/operations-web/src/features/products/AiModelPicker.jsx`, `useProductDraft.js`, `RegisterPage.jsx`, `ProductModal.jsx`, `App.jsx`, `tests/test_registration_ai.py`, `tests/test_endpoint_usage.py`, `tests/test_backend_api.py` |
