# CLIENTE-01 — Tienda del comprador y pago de prueba

**Estado:** Aceptado por el usuario el 2026-11-26 como ampliación confirmada del alcance (ADR-007). Prototipo implementado en `apps/customer-web` y `apps/backend`. **Pendiente:** ejecutar `pytest`, `npm run build` y validar en navegador; el shell del entorno falla al iniciar `pwsh`.

## Identificador y trazabilidad

`CLIENTE-01` es un identificador técnico incremental que amplía **CU-05** (registrar salidas) y **CU-07** (supervisar registros), y comparte la decisión **ADR-007** con la ampliación de `scope.md`. No crea nuevos casos de uso, entidades de negocio, actores, tecnologías ni reglas numeradas de la serie original: reutiliza CU-05, CU-07, EN-01…EN-06, AN-02/AN-03, TN-02/TN-03, RF-31…RF-33 y RN-15/RN-16. El actor comprador ya estaba previsto en el modelo; ahora tiene interfaz y autenticación propias. La IA no participa en el pago ni en el inventario.

## Problema y objetivo

**Confirmado por el usuario:** quiere una aplicación de clientes con la misma paleta, tamaños de texto, menú y perfil que `operations-web` (con rol `Cliente`), alimentada por la base actual del repositorio, con backend y con el flujo de checkout/pago de prueba de la implementación de su compañero. Rechazó una demo solo de interfaz y la opción de «no pagar».

**Derivado de la revisión:** el esquema local ya contiene todas las tablas; la referencia del companion tiene problemas de interfaz y un seed destructivo, por lo que se porta la lógica, no el producto tal cual.

**Objetivo:** que el comprador descubra ofertas vigentes, reserve productos por diez minutos y confirme con un pago de prueba sin que el navegador pueda decretar el éxito del cobro ni duplicar el descuento de stock.

## Alcance incluido / excluido

### Incluido

- Menú `Inicio`, `Bodegas`, `Mi cesta`, `Mis pedidos`, con barra lateral en escritorio y botón de hamburguesa inferior que despliega esas cuatro secciones más «Mi cuenta» bajo 720 px. `Perfil` no se repite como etiqueta de menú: se abre desde la tarjeta de cuenta con rol `Cliente` y, en móvil, desde el panel desplegable (ADR-007 y ADR-009).
- Catálogo público desde `/customer/stores` y `/customer/offers`; filtros por bodega, precio, vencimiento y búsqueda; disponibilidad = stock − reservas activas. El catálogo de ofertas del backend se deriva en `ensure_schema()` de los productos activos de Bodega San Martín: todos se publican a su precio real y solo un subconjunto fijo recibe 20% de descuento; las ofertas existentes no se sobrescriben. La tienda no mantiene un catálogo local.
- Cesta de una sola bodega; alta, cambio de cantidad y eliminación; total calculado desde `current_price`.
- Registro/login de comprador con token HMAC `rol = 'cliente'`; `/customer/auth/me`.
- Pedido reservado por diez minutos con UUID idempotente; el método de pago elegido se persiste en `Pago` y se devuelve en `payment_mode`; historial con todos los estados.
- Selector de método en la cesta con `GET /customer/payment-methods`: `Simular pago` (`LOCAL_SIMULATION`) y checkout de Mercado Pago de prueba (`MERCADOPAGO_TEST`), disponible solo si el backend tiene credenciales de prueba; verificación server-side y webhook firmado.
- Un único descuento de stock compartido con `POST /sales` mediante `sales_service.decrement_stock_once()` y `approve_reserved_order()`. No existe compra local: sin backend no hay catálogo ni checkout; la UI muestra el error en lugar de datos inventados.
- Seed opcional y no destructivo de ofertas y comprador demo.
- Favicon servido desde `public/favicon.png` y escala móvil legible con piso de `9px × escala`, sin barra inferior fija de secciones (ADR-009).

### Excluido

- Pagos reales, cobro con dinero, facturación, proveedores, entregas y contabilidad.
- Aprobación de inventario desde el navegador o desde una sugerencia de IA.
- Creación de jefes/empleados, sobreescritura de contraseñas o precios desde el seed de cliente.
- `Movimiento`/`DetalleMovimiento`, lotes y responsable de movimiento: RN-03 sigue pendiente.
- Edición, anulación y reembolso de pedidos.
- Modo demo o catálogo local como sustituto del checkout: no existe; sin backend la tienda informa el error. El flujo de pago de prueba aprobado por el backend es el único camino de compra.

## Actores y permisos

| Actor | Permiso |
|---|---|
| Comprador | Registro/login; ve catálogo, su cesta local y sus pedidos; inicia o consulta el pago de sus propios pedidos. |
| Jefe (AN-02) | Ve `Ventas` con solo compras pagadas; no aprueba pagos desde la tienda. Hereda operaciones del empleado por RN-02. |
| Empleado (AN-03) | Ve `Ventas` de su bodega; no accede a `/customer/*` con su token. |
| IA | No interviene: no aprueba, genera compras ni modifica inventario. |

## Precondiciones y postcondiciones

**Precondiciones:** `Cliente` activo; oferta activa y vigente; `ProductosBodega` activo con vencimiento futuro y stock suficiente descontando reservas; las líneas pertenecen a una sola bodega; UUID idempotente.

**Postcondiciones de reserva:** una `Compra` en `pendiente` con `reserva_hasta` y `request_hash`, sus `DetalleCompra` y `ReservaCompra` activas. El stock **no cambia**.

**Postcondiciones de pago aprobado:** la reserva pasa a `consumida`, la compra a `pagado` con `fecha_pago`, se inserta el `Pago` y cada producto baja exactamente su cantidad una vez. Cualquier fallo revierte la transacción.

**Postcondiciones de rechazo/expiración:** reservas liberadas, compra `rechazado`/`expirado`, sin descuento. Un cobro acreditado tarde queda `pago_en_revision` para revisión humana y no descuenta stock.

## Flujo principal

1. El comprador se registra o inicia sesión; el token se guarda en `bodesmart_customer_token`.
2. La app carga bodegas y ofertas. El backend expira reservas vencidas y calcula disponibilidad.
3. El comprador agrega ofertas a la cesta, elige método de pago y la UI valida bodega única, vencimiento y disponible.
4. `POST /customer/orders` crea la reserva con idempotencia y guarda el método; el pedido aparece en `Mis pedidos` en `pendiente`.
5. El comprador confirma: `Simular pago` aprueba en local o `Pagar con Mercado Pago de prueba` abre la pasarela. El navegador no decide el resultado.
6. El backend consulta al proveedor, valida importe, referencia, moneda, cuenta y firma, y llama a la aprobación compartida.
7. Las vistas `Mis pedidos` y `Ventas` leen estados distintos por diseño: todas las del comprador, solo `pagado` para la bodega.

## Reglas y trazabilidad de código

| Regla | Implementación | Prueba |
|---|---|---|
| RN-15/RN-16: venta = pago aprobado con descuento atómico | `apps/backend/sales_service.py`, `routers/customer.py` | `tests/test_sales.py`, `tests/test_customer_flow.py` |
| Pedido reservado no descuenta; expirado libera | `routers/customer.py`, `sales_service.release_expired()` | `test_expiry_releases_stock_and_prevents_payment` |
| Idempotencia y una sola bodega por pedido | `POST /customer/orders` | `test_idempotency_and_key_conflict`, `test_mixed_stores_rejected` |
| Verificación server-side del pago de prueba | `checkout`, `verify_payment`, `payment_webhook` | `test_external_payment_is_verified_server_side`, `test_signed_webhook_reconciles_payment_once` |
| Historial visible del comprador | `GET /customer/orders`, `OrdersPage.jsx` | `test_history_shows_pending_and_paid_orders`, `tests/test_customer_contract.py` |
| Paridad visual con `operations-web` | `apps/customer-web/src/styles.css`, `CustomerLayout.jsx` | `test_customer_ui_reuses_operations_visual_tokens` |
| Shell móvil legible y favicon compartido | `index.html`, `CustomerLayout.jsx`, `styles.css` | `tests/test_web_shell_contract.py` |

## Preguntas abiertas

- ¿Se publicará `customer-web` en un dominio propio y con `CORS_ORIGINS` de producción? No hay decisión confirmada.
- ¿Qué cuenta de Mercado Pago de prueba y qué webhook se usarán en el entorno compartido? Requiere credenciales reales de prueba.
- La precisión del checkout depende de la disponibilidad del proveedor; no hay métricas ni SLA del prototipo.
