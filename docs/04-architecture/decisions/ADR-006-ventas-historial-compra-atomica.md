# ADR-006: Historial de ventas y compra atómica para `operations-web`

**Estado:** Aceptado por el usuario el 2026-11-26. El usuario pidió una sección `Ventas` visible para jefe y empleado, pidió revisar el `customer-web` y las tablas agregadas por su compañero en `C:\projects-4\project-software-design`, autorizó sembrar compras demo y confirmó que la trazabilidad de este corte sea solo `Compra` + descuento atómico de stock, sin tablas `Movimiento`/`DetalleMovimiento`. Prototipo implementado; pendiente de `pytest`, `npm run build` y validación en navegador.

**Fecha:** 2026-11-26

## Contexto

`operations-web` no tenía ninguna vista de ventas. El esquema local ya traía `Cliente`, `Oferta`, `Compra`, `DetalleCompra`, `Carrito`, `DetalleCarrito` y `Pago`, pero ningún endpoint ni interfaz los usaba. Al momento de esta decisión `customer-web` no existía en este repositorio; posteriormente se incorporó con ADR-007 y consume `/customer/*`. En el checkout revisado de `C:\projects-4\project-software-design`, el backend expone `/customer/*`, crea pedidos `pendiente` con reserva de diez minutos y solo descuenta `ProductosBodega.stock` en `_approve`, cuando el pago se aprueba y la compra pasa a `pagado`. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` no toman existencias.

El usuario necesita que el historial sea coherente: si muestra «10 kg de mango verde vendidos», antes debió haber al menos 10 kg y el saldo ya debió actualizarse. Por eso no basta con leer filas sueltas: la lectura y la escritura deben compartir la misma definición de venta.

## Decisión

- Incorporar **VENTAS-01** como ampliación de CU-05 y CU-07, con RF-31…RF-33 y RN-15/RN-16. No crea nuevos identificadores CU/EN/RN/AN/TN.
- Alinear `apps/database/database.sql` y las migraciones de `ensure_schema()` con el contrato revisado: `Oferta.id_bodega`/`.precio_original`, `Compra.reserva_hasta`/`.idempotency_key`/`.request_hash`/`.fecha_pago`, `DetalleCompra.id_oferta`, columnas de proveedor en `Pago` y la tabla `ReservaCompra` con índice parcial por reservas activas.
- Definir una sola venta: `Compra.estado = 'pagado'`. `GET /sales` devuelve solo esas filas de la bodega del token, con cliente, fecha de pago, total y líneas con cantidades y precios congelados. Jefe y empleado pueden verla; un token `cliente` no puede acceder.
- `POST /sales` crea la compra pagada en una transacción:
  - exige jefe/empleado, `id_cliente` de un `Cliente` activo y 1…20 líneas con `id_producto` y `cantidad` enteros positivos sin repetidos;
  - bloquea `ProductosBodega` con `FOR UPDATE OF pb`, valida producto activo, vencimiento futuro o nulo, precio positivo y stock suficiente;
  - descuenta con `UPDATE ... WHERE stock >= cantidad RETURNING stock` y falla si no hay fila, con rollback de todo lo anterior;
  - guarda `Compra`, `DetalleCompra`, `ReservaCompra` en estado `consumida` y una traza `Pago` con `metodo_pago = 'LOCAL_SIMULATION'`;
  - usa `idempotency_key` UUID con lock advisory para no repetir venta ni descuento.
- `id_oferta` es opcional; si se envía, debe estar vigente para el producto y la bodega, y congela `precio_oferta`. No se integra Mercado Pago ni cobro real.
- `sales_service.ensure_demo_sales()` siembra tres compras sintéticas de `cliente.demo@bodesmart.local` con claves fijas. Se ejecuta en cada arranque pero no vuelve a descontar si la clave ya existe. `seed.sql` no inserta compras para evitar dobles descuentos en bases ya creadas.
- La UI `Ventas` es de solo lectura, sin botones de cobro ni edición. Su estado vacío explica que las compras aparecerán cuando se confirmen desde la tienda de clientes.

## Consecuencias

- `GET /sales` y `POST /sales` comparten `sales_service.py`: la lectura no puede inventar una venta que el descuento no respaldó.
- El historial no incluye lotes ni responsable de movimiento. RN-03 y el registro EN-05/EN-06 siguen pendientes de integración; este checkout opera sobre saldos agregados por producto y bodega, igual que el backend revisado.
- En este corte no se incorporaba autenticación de `cliente` ni interfaz de comprador; `POST /sales` quedaba como contrato. ADR-007 amplió el alcance y resolvió la autenticación con `/customer/auth/*` en este mismo backend: la afirmación anterior queda superada, no contradicha.
- No se envían correos ni teléfonos al frontend; solo nombre y apellido del comprador como identificación mínima.
- Las compras demo cambian el stock inicial de los productos elegidos. No son datos reales y se pueden eliminar limpiando las tres claves de idempotencia y recalculando stock solo de forma consciente.
- Pendiente: ejecutar `tests/test_sales.py`, `tests/test_backend_api.py`, `tests/test_endpoint_usage.py`, `npm run build` y comprobar en el navegador que la sección aparece para ambos roles y que el stock baja una sola vez.

## Alternativas descartadas

- **Solo lectura de `Compra`:** cualquier inserción futura podría descontar mal o no descontar. Descartada porque no garantiza RN-04.
- **UI vacía hasta `customer-web`:** no permitiría verificar la coherencia ni dejar un contrato claro para la tienda futura. Descartada por petición explícita de datos demo.
- **Crear `Movimiento` y `DetalleMovimiento` ya:** habría ampliado el alcance y requerido definir lotes y responsable sin información confirmada. El usuario eligió `Compra` + stock atómico.
