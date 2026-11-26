# Reglas de negocio

| Código | Regla | Tipo | Casos |
|---|---|---|---|
| RN-01 | Administrador gestiona cuentas y accesos. | Autorización | CU-01 |
| RN-02 | Jefe gestiona bodega y empleados y realiza operaciones del empleado. Cada empleado accede solo a su bodega. | Autorización | CU-02…CU-09 |
| RN-03 | Toda entrada/salida indica productos, lotes, cantidades positivas y responsable. | Validación | CU-04, CU-05, CU-07 |
| RN-04 | Salida no supera existencias; al confirmar stock se descuenta una sola vez. | Restricción | CU-05, CU-06 |
| RN-05 | Total venta = suma de cantidad × precio aplicado por producto. | Cálculo | CU-05 |
| RN-06 | Productos vencidos o deteriorados no se venden; retiro es merma. | Restricción | CU-05, CU-06, CU-08 |
| RN-07 | Modificación de precios: jefe en cualquier fila; empleado solo en filas activas, no bloqueadas y creadas por él. Aprueba descuentos/promociones solo el jefe. Ver ADR-001. | Autorización | CU-02, CU-08 |
| RN-08 | Sugerencias IA de descuentos, aumentos de precio y reposición requieren aprobación del jefe; puede modificarlas o rechazarlas. La IA no aplica cambios ni modifica inventario. Reposición aprobada no genera compra ni cambia stock. | Autorización | CU-08, CU-09 |
| RN-09 | Promoción: precio positivo menor al regular; fecha fin posterior a inicio; aplica durante vigencia y con stock apto. | Validación | CU-05, CU-08 |
| RN-10 | El empleado edita únicamente filas activas, no bloqueadas, cuyo creadoPor es su cuenta; no elimina ni desactiva. Ver ADR-001. | Autorización | CU-02, CU-03 |
| RN-11 | El jefe puede bloquear/desbloquear cualquier fila; bloqueada solo la edita el jefe. El jefe desactiva en lugar de borrar, conservando historial. Ver ADR-001. | Autorización | CU-02, CU-03 |
| RN-12 | En registro asistido, `Foto` propone nombre, ícono, categoría, cantidad (stock inicial) y unidad; `Voz` transcribe esos campos y también `precio_venta`, `fecha_vencimiento` y `codigo_barras` cuando se dictan explícitamente; `Código` propone nombre, ícono, categoría, unidad y código desde Open Food Facts, pero no cantidad. Todo lo propuesto o dictado es revisable por el usuario. Ver ADR-005. | Validación | CU-02, CU-04 |
| RN-13 | `precio_venta` y `fecha_vencimiento` son sugerencias editables y no se aplican sin confirmación. En `Voz` su fuente es el dictado del usuario: se transcriben solo si se dicen explícitamente, con fecha ISO `AAAA-MM-DD`, sin estimar ni deducir vida útil. En `Foto` siguen manuales. En `Código`, Open Food Facts no expone esos campos y siguen manuales. Ver ADR-005. | Validación | CU-02, CU-04 |
| RN-14 | Existe un catálogo persistente de categorías: cada producto guarda una sola categoría por su nombre; el usuario puede crear una nueva categoría desde el registro, se reutiliza de forma insensible a mayúsculas/minúsculas y se conserva en la base para futuros registros. Es un detalle de implementación de EN-03, no una nueva entidad de negocio. Ver RF-29 y ADR-005. | Validación | CU-02 |
| RN-15 | Solo se presenta como venta una `Compra` en estado `pagado`. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` no descontaron stock y no aparecen en `Ventas`. Ver RF-31, RF-33 y ADR-006. | Validación | CU-05, CU-07 |
| RN-16 | Toda compra pagada identifica cliente, bodega, productos, cantidades positivas y precios congelados; el descuento de stock y el cambio a `pagado` ocurren en una sola transacción y una clave de idempotencia impide repetirlos. Ver RF-32 y ADR-006. | Validación | CU-05 |
| RN-17 | En `Foto` y `Voz`, el modelo Gemini debe pertenecer a la allowlist del backend (`GEMINI_ALLOWED_MODELS`). `GET /ai/models` expone solo identificadores autorizados; un modelo arbitrario enviado por el navegador se rechaza con `400`. La clave permanece solo en el backend. Ver RF-34 y ADR-005. | Validación | CU-02 |

## Estado de las reglas de registro asistido

- **Confirmado para el prototipo:** RN-12 y RN-13 según la decisión vigente de ADR-005; RN-14 según el catálogo implementado en `apps/database/database.sql`, `apps/database/seed.sql` y `apps/backend/database.py`; RN-17 según la allowlist de `config.py`, `GET /ai/models` y la validación en `POST /products/extract`.
- **Derivado:** la creación de categoría desde el selector no crea producto ni movimiento; el alta de producto requiere la confirmación explícita del formulario (RN-03, RN-08).
- **Pendiente:** validar con audio real la precisión del dictado de precio, fecha y dígitos, y ejecutar las pruebas automatizadas en el entorno definido en `docs/06-quality/README.md`.

## Estado de las reglas de ventas

- **Confirmado por el usuario:** las tablas de compras del `customer-web` del compañero son la referencia y se siembran compras demo; la trazabilidad se limita a `Compra` + descuento atómico de stock, sin tablas `Movimiento`/`DetalleMovimiento` en este corte.
- **Derivado:** RN-15 y RN-16 se aplican al contrato `GET/POST /sales` y a la vista `Ventas`; el cuadrante de lotes/responsable de RN-03 sigue pendiente porque este checkout opera sobre saldos por producto y bodega.
- **Resuelto por ADR-007:** la interfaz y la autenticación del comprador ya viven en este repositorio con `/customer/auth/*`; el pago de prueba usa Mercado Pago solo en modo test, sin cobro real.
- **Pendiente:** pasarela de cobro real y prismas de lote/responsable del CU-05.
