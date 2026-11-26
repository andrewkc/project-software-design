# Tareas — REG-IA

| Tarea | Estado | Resultado verificable / criterio de finalización |
|---|---|---|
| Confirmar expansión de alcance con el usuario | Hecho | Usuario confirmó foto, código y voz; ADR-005 registra la decisión y sus ampliaciones posteriores. |
| Resolver política de campos y privacidad | Hecho | Cantidad manual en `Código`; precio/vencimiento manuales en `Foto` y `Código`; en `Voz` se transcriben solo los campos dictados, sin estimar vida útil; campos revisables; solo datos de prueba. |
| Revisar y aprobar la especificación | Hecho para el prototipo | `spec.md` con actores, reglas RN-12/RN-13/RN-14/RN-17 y criterios de aceptación. |
| Registrar la decisión técnica | Hecho | `ADR-005` y trazabilidad en `traceability.md`, incluido el cambio de decisión del usuario. |
| Definir el contrato HTTP y el esquema de salida | Hecho | `POST /products/extract`, `GET /ai/models` y `GET/POST /categories` documentados en `plan.md`. |
| Implementar el adaptador de registro | Hecho | `apps/backend/registration_ai.py` con modos, MIME, tamaño, esquema de voz de ocho campos, consulta a Open Food Facts, categorías dinámicas y saneamiento. |
| Implementar el endpoint autenticado | Hecho | Router registrado; sin escrituras de producto en la extracción; errores `400`/`503` controlados. |
| Implementar captura real de imagen y código | Hecho | `PhotoCapture` y `BarcodeCapture` entregan dataURL y dígitos; el backend de `Código` consulta Open Food Facts. |
| Implementar el botón alterno de cámara en `Código` | Hecho | El botón del medio captura el frame con la cámara lista y reinicia la cámara si está apagada; intenta `BarcodeDetector` sobre el canvas; etiqueta «Usar imagen del código» / «Encender cámara»; «Subir imagen» y «Leer dígitos» siguen disponibles. |
| Implementar grabación real de voz con transcripción completa | Hecho | `VoiceCapture` usa `MediaRecorder`; el prompt/schema de `voice` transcribe los ocho campos dictados, con precio/fecha solo explícitos, fecha ISO `AAAA-MM-DD` y sin estimar vida útil. |
| Ampliar el selector de Ícono con paridad | Hecho | `PRODUCT_EMOJIS` tiene 124 emojis con keywords; `ICONOS` del backend tiene paridad exacta; disponible en Foto/Código/Texto/Voz. |
| Implementar Categoría expandible persistente | Hecho | `Categoria` en `database.sql`, nueve categorías base en `seed.sql`, migración y helpers en `database.py`, router de categorías, `CategoryPicker` estilo Notion con «Agregar nueva categoría», una categoría por producto y reutilización case-insensitive. |
| Convertir el formulario a estado controlado | Hecho | `ProductForm` sin valores de demostración; recibe y devuelve un borrador editable en todos los modos. |
| Conectar la UI de Registrar, el modal y el inventario | Hecho | `useProductDraft()` compartido; categorías y modelos cargados en `App.jsx` con `Promise.all`; categorías pasadas también a `InventoryPage`; `addCategory` actualiza el estado. |
| Implementar selector de modelo con allowlist | Hecho | `GEMINI_ALLOWED_MODELS` en `config.py`/.env/compose; `GET /ai/models`; `resolve_model()` rechaza ids arbitrarios con `400`; `AiModelPicker` aparece solo en Foto/Voz en la página y el modal; la clave no llega al frontend. |
| Actualizar pruebas automatizadas | Hecho (prototipo) | `tests/test_registration_ai.py` cubre voz completa, categorías dinámicas, paridad de emojis, alternancia de cámara y persistencia estática; `test_backend_api.py` incluye creación/reutilización de categorías; `test_endpoint_usage.py` cubre `GET /ai/models` y `GET/POST /categories`. Ejecución pendiente. |
| Corregir la versión de Interactions API | Hecho | La prueba real con foto devolvió `400` en `v1`; el default compartido pasó a `v1beta/interactions`. |
| Sustituir `google_search` en `Código` | Hecho | La prueba real devolvió `429` en plan gratuito; se consulta Open Food Facts y se muestra mensaje de registro manual si no hay coincidencia. |
| Ejecutar pruebas y compilación | Pendiente | Ejecutar `pytest` y `npm run build` y registrar los resultados en `docs/06-quality/README.md`. |
| Validar foto/código/voz con clave real | Pendiente | `Foto`/`Voz` con multimedia sintético y `Código` con un EAN propio/sintético; revisar saneamiento, transcripción y ausencia de mutación. Probar el default y el modelo alterno por separado; un `503` por alta demanda no indica fallo de código. |
| Validar precisión del dictado | Pendiente | Probar precios, fechas y dígitos dictados con grabaciones reales; confirmar que lo no dictado queda vacío y que no se estima vencimiento. |
| Verificar cuota de multimedia | Pendiente | Revisar el proyecto Gemini del usuario y registrar el resultado. *Search grounding* quedó fuera del corte. |
| Decidir persistencia de sugerencias | Pendiente | Si se requiere auditoría, ampliar EN-08 en un nuevo corte. Las categorías ya se persisten por decisión del usuario. |

Las tareas marcadas como **Hecho** describen código escrito en el prototipo; **no implican** que la integración multimodal haya sido validada contra Gemini, que las pruebas se hayan ejecutado en este entorno ni que el producto esté terminado.
