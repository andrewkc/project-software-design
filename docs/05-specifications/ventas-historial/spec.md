# VENTAS-01 — Historial de ventas y compra atómica

**Estado:** Aceptado por el usuario el 2026-11-26 como ampliación confirmada del alcance. Prototipo implementado en backend, esquema e interfaz. **Pendiente:** ejecutar `pytest` y `npm run build`, reconstruir los contenedores y validar en navegador con los tres roles y el stock.

## Identificador y trazabilidad

`VENTAS-01` es un identificador técnico incremental que amplía **CU-05** (registrar salidas) y **CU-07** (supervisar registros). La decisión quedó registrada en **ADR-006**. No crea nuevos casos, entidades de negocio, actores, tecnologías ni reglas numeradas de la serie original: reutiliza CU-05, CU-07, EN-01…EN-06, AN-02/AN-03, TN-02/TN-03, RF-31…RF-33 y RN-15/RN-16.

## Problema y objetivo

**Confirmado por el usuario:** quiere una sección `Ventas` visible para `Jefe` y `Empleado` con el historial de compras de usuarios `cliente`, coherente con el inventario. Si un registro dice que se vendieron 10 kg de mango verde, antes debió existir ese stock y luego de la compra debe haberse actualizado el saldo. El usuario confirmó además que las tablas del `customer-web` implementado por su compañero son la referencia, que se siembren datos demo y que la trazabilidad sea solo `Compra` + descuento atómico de stock, sin tablas `Movimiento`/`DetalleMovimiento`.

**Derivado de la revisión:** la futura tienda crea pedidos `pendiente` con reserva de diez minutos y solo descuenta inventario cuando el pago aprueba y la compra pasa a `pagado`. Por eso «venta» significa exactamente `Compra.estado = 'pagado'`.

**Objetivo del incremento:** que `Ventas` muestre únicamente compras pagadas con detalle verificable, y que la escritura y el descuento de stock compartan una sola transacción para que la lectura nunca contradiga al inventario.

## Alcance incluido / excluido

### Incluido

- Navegación `Ventas` para jefe y empleado, en escritorio y móvil, sin distinción de roles dentro de la sección; en móvil se alcanza desde el menú desplegable de hamburguesa, no desde una barra inferior fija (ADR-009).
- `GET /sales`: compras `pagado` de la bodega del token, ordenadas por fecha de pago, con cliente, fecha, total, método de pago local y líneas con producto, cantidad, precio unitario y subtotal congelados.
- `POST /sales`: alta transaccional de una compra pagada de un `Cliente` activo, con validación de cantidades positivas, producto activo, vencimiento futuro o nulo, precio positivo, stock suficiente, idempotencia opcional y descuento condicional de stock.
- Esquema y migraciones idempotentes: columnas de `Oferta`, `Compra`, `DetalleCompra` y `Pago` del contrato revisado, más `ReservaCompra` con índice parcial.
- Tres compras demo sintéticas sembradas desde el backend con claves de idempotencia fijas y stock descontado una sola vez.
- Estado vacío explícito cuando no haya compras pagadas.
- La gráfica lineal del inicio «Ventas acumuladas» se calcula con el mismo `GET /sales` que consume la sección: agrupa `total` por día de `fechaPago`, acumula en orden cronológico y termina en el mismo total del resumen de `Ventas`. No genera fechas ni importes de ejemplo; si no hay compras pagadas, muestra el estado vacío y un enlace a `Ventas`.

### Excluido

- Interfaz de comprador, carrito y autenticación de `cliente` dentro de esta funcionalidad: viven en la app `customer-web` (ADR-007) y no forman parte de la vista `Ventas`.
- Cobros reales, facturación, entregas, contabilidad, proveedores ni sugerencias de IA de compra. Mercado Pago se usa solo en modo de prueba (ADR-007).
- Tablas `Movimiento` y `DetalleMovimiento`, lotes, responsable de movimiento y vencimientos por lote. RN-03 y EN-04/EN-05/EN-06 siguen pendientes de integración.
- Pedidos `pendiente`, `expirado`, `rechazado` o `pago_en_revision` en el historial: no descontaron stock, por lo que no son ventas.
- Datos reales de clientes, correos o teléfonos en la vista. El demo usa `cliente.demo@bodesmart.local`.
- Edición, anulación o reembolso desde `Ventas`: la sección es de solo lectura.

## Actores y permisos

| Actor | Permiso |
|---|---|
| Jefe (AN-02) | Ve `Ventas` y puede llamar `GET/POST /sales`; hereda operaciones del empleado según RN-02. |
| Empleado (AN-03) | Ve `Ventas` y puede llamar `GET/POST /sales` solo para su bodega asignada. |
| Cliente | Origen de los datos en la futura tienda; hoy no se autentica en este backend. Un token `cliente` recibe `403`. |
| IA | No interviene: no aprueba, genera compras ni modifica inventario por sugerencia. |

## Precondiciones y postcondiciones

**Precondiciones:** sesión válida de jefe o empleado; `Cliente` activo para `POST /sales`; producto activo en `ProductosBodega` de la bodega resuelta por el token; stock suficiente; oferta vigente solo si se envía `id_oferta`.

**Postcondiciones de lectura:** `GET /sales` no muta inventario y devuelve cero o más compras pagadas de una sola bodega.

**Postcondiciones de escritura:** una sola `Compra` en estado `pagado`, sus `DetalleCompra`, una `ReservaCompra` por producto en estado `consumida` y un `Pago` local. El stock de cada producto baja exactamente `cantidad` una vez. Si cualquier validación falla, la transacción se revierte y no queda compra ni descuento.

## Flujo principal

1. El usuario inicia sesión como jefe o empleado. La app carga `GET /sales` junto con el resto de los datos iniciales.
2. El backend resuelve `bodega_id_for(conn, who)` desde el token y filtra por ese identificador.
3. Se ejecuta `release_expired(conn)` para mantener la máquina de estados del checkout coherente; los pedidos expirados libran reservas pero no se muestran.
4. Se consultan solo las filas con `estado = 'pagado'`, ordenadas por `COALESCE(fecha_pago, fecha_compra) DESC, id DESC`.
5. Para cada compra se cargan las líneas con nombre, icono, unidad, cantidades y precios congelados, el nombre del cliente y la traza de pago.
6. La UI resume número de compras, total vendido y unidades, y lista cada pedido con sus líneas. Si no hay filas, muestra el estado vacío.

## Alta transaccional

`create_paid_sale(conn, ...)` es la única función que descuenta stock en este corte:

1. Normaliza y ordena las líneas; exige 1…20 productos sin repetir y cantidades enteras positivas.
2. Calcula un `request_hash` y toma un `pg_advisory_xact_lock` por `idempotency_key` UUID si se envió; una clave repetida con el mismo contenido devuelve la compra existente sin volver a descontar.
3. Valida `Cliente.estado = 'activo'`.
4. Bloquea cada `ProductosBodega` con `FOR UPDATE OF pb`; valida producto activo, vencimiento, precio y stock.
5. Inserta `Compra` pagada, descuenta con `UPDATE ... WHERE stock >= cantidad RETURNING stock`, inserta detalle, reserva consumida y pago local.
6. Si una fila de actualización desaparece, falla y se revierte toda la transacción.

## Alternativas y excepciones

| Situación | Comportamiento |
|---|---|
| Token de `cliente` u otro rol | `403` en `GET/POST /sales`; la navegación no muestra `Ventas` porque la app solo gestiona jefe/empleado. |
| Cuenta sin bodega asignada | `401`; no se filtra información de otras bodegas. |
| Cliente inactivo o inexistente | `404`; no se crea la compra. |
| Cantidad no entera, cero, negativa o producto repetido | `400`. |
| Producto ausente en la bodega, inactivo, vencido o sin stock | `404`/`409`; rollback sin descuento. |
| `id_oferta` inexistente o fuera de vigencia | `409`; rollback sin descuento. |
| Idempotency key repetida con otros datos | `409`; no se modifica la compra original. |
| Demo editado o eliminado por el usuario | `ensure_demo_sales()` usa un savepoint por compra y continúa; la vista puede quedar con menos de tres registros. |
| Sin compras pagadas | Estado vacío explicativo, sin stock modificado. |

## Reglas de negocio

- **RN-02/RN-05:** el jefe puede operar como empleado; el empleado consulta solo su bodega. `bodega_id_for` aplica el filtro antes de leer o escribir.
- **RN-03:** las cantidades son positivas; el responsable y el lote siguen pendientes para este corte (ver ADR-006).
- **RN-04:** una salida no supera el stock disponible y descuenta una sola vez. Se usa `FOR UPDATE` y el `UPDATE` condicional dentro de la transacción.
- **RN-05:** no se vende producto vencido o registrado como deteriorado; se validan `fecha_vencimiento` y `estado`.
- **RN-06:** el precio vigente se congela en `DetalleCompra.precio_unitario`; si hay oferta válida, se congela `precio_oferta`.
- **RN-15:** solo `Compra.estado = 'pagado'` se presenta como venta.
- **RN-16:** cliente, bodega, productos, cantidades y precios quedan identificados en una sola transacción con idempotencia.

## Datos y entidades

- **EN-01/EN-02:** bodega del token y jefe/empleado que consulta; ninguna lectura cruza bodegas.
- **EN-03:** catálogo de productos; el detalle guarda `id_producto` y el nombre congelado para la vista.
- **EN-04/EN-05/EN-06:** lotes y movimientos siguen pendientes. El saldo agregado de `ProductosBodega` es la fuente de stock de este corte.
- **EN-07:** `Oferta` con `id_bodega`, `precio_original` y vigencia; opcional en una venta.
- Tablas de implementación tomadas del `customer-web` revisado: `Cliente`, `Oferta`, `Compra`, `DetalleCompra`, `Pago` y `ReservaCompra`. No son nuevas entidades de negocio ni sustituyen EN-04/EN-05/EN-06.

## Criterios de aceptación

| Criterio | Estado en el prototipo | Validación pendiente |
|---|---|---|
| `Ventas` aparece para jefe y empleado en escritorio y móvil. | Implementado | Revisión en navegador con ambos roles. |
| El historial muestra solo compras `pagado` de la bodega del token. | Implementado | Prueba HTTP y verificación de aislamiento. |
| Cada línea muestra producto, cantidad, precio unitario y subtotal congelados. | Implementado | Prueba HTTP y revisión visual. |
| El descuento de stock y el alta de la compra ocurren en una transacción y una sola vez. | Implementado | `tests/test_sales.py` contra la base real. |
| Una venta sin stock suficiente, con producto vencido o con cliente inactivo se rechaza sin mutar inventario. | Implementado | Prueba HTTP de integración. |
| Las tres compras demo son sintéticas y no se duplican al reiniciar. | Implementado | Arranque repetido y consulta de stock. |
| Estado vacío explícito si no hay compras pagadas. | Implementado | Revisión visual. |
| `pytest` y `npm run build` pasan con los entornos definidos. | No verificado en este entorno | Ejecutar y registrar en `docs/06-quality/README.md`. |

## Escenarios de prueba

| Escenario | Resultado esperado |
|---|---|
| Jefe abre `Ventas` con la base sembrada | Tres compras pagadas con cliente, fecha, total y líneas; stock ya descontado una vez. |
| Empleado abre `Ventas` | Misma vista de su bodega, sin acceso a otras bodegas. |
| Pedido `pendiente`, `expirado`, `rechazado` o `pago_en_revision` | No aparece; no descontó stock. |
| `POST /sales` con `cantidad` > stock | `409`; compra y stock sin cambios. |
| `POST /sales` con producto vencido o inactivo | `409`; sin descuento. |
| `POST /sales` repetido con la misma idempotency key | Devuelve la misma compra; stock baja una sola vez. |
| `POST /sales` con idempotency key repetida y otro contenido | `409`. |
| Reiniciar backend con las compras demo ya sembradas | No hay nuevas compras ni descuentos adicionales. |
| Token de `cliente` | `403` en `/sales`. |

## Dependencias

- Backend FastAPI existente, token HMAC y `bodega_id_for`.
- PostgreSQL con el esquema base; las migraciones viven en `ensure_schema()` para bases ya creadas.
- Contrato de compras del `customer-web` de `C:\projects-4\project-software-design` como referencia, sin copiar su autenticación ni su pasarela.
- No se requiere `GEMINI_API_KEY`: esta funcionalidad no llama a IA.
