# Entidades del negocio

| Código | Entidad | Atributos principales |
|---|---|---|
| EN-01 | Cuenta de usuario | idCuenta, nombre, correo, rol, estado |
| EN-02 | Bodega | idBodega, nombre, dirección, ubicación, presupuestoReposicion |
| EN-03 | Producto | idProducto, nombre, categoría, unidadMedida, precioVenta, estado, creadoPor (EN-01), bloqueado, bloqueadoPor (EN-01) |
| EN-04 | Lote | idLote, fechaIngreso, fechaVencimiento opcional, cantidadDisponible, costoUnitario |
| EN-05 | Movimiento de inventario | idMovimiento, fechaHora, tipo, motivo, total opcional |
| EN-06 | Detalle de movimiento | idDetalle, cantidad, importeUnitario opcional, subtotal opcional |
| EN-07 | Promoción | idPromocion, precioPromocional, fechaInicio, fechaFin, estado |
| EN-08 | Sugerencia de IA | idSugerencia, fechaGeneracion, tipo, cantidadSugerida/precioSugerido, justificación, estadoDecision, fechaDecision, cantidadAprobada/precioAprobado |

**Nota sobre EN-03 (detalle de implementación, no nueva entidad de negocio):** `categoria` se guarda como el nombre de una sola categoría elegida para el producto y se persiste en el catálogo `Categoria` creado en `apps/database/database.sql`. La relación es lógica por nombre (reutilizable de forma insensible a mayúsculas/minúsculas), no una foreign key física; `apps/database/seed.sql` siembra nueve categorías base y `apps/backend/database.py` migra los nombres ya usados por `Producto` con deduplicación por `lower(btrim(categoria))`. Ver RN-14 y RF-29.

**Nota sobre VENTAS-01 (detalle de implementación, no nueva entidad EN):** `Cliente`, `Oferta`, `Compra`, `DetalleCompra`, `Pago` y `ReservaCompra` son tablas del contrato de compras tomadas del `customer-web` implementado por el compañero. Materializan la venta del CU-05 sobre saldos por producto y bodega: `Compra.estado = 'pagado'` es la única venta y su detalle conserva cantidades y precios congelados. No sustituyen a EN-04 (Lote), EN-05 (Movimiento) ni EN-06 (Detalle de movimiento), que siguen pendientes de integración. Ver RN-15, RN-16 y ADR-006.

## Semántica
Stock = suma de cantidades disponibles de lotes. Cada detalle corresponde a un lote. Una venta que usa varios lotes genera varias líneas en una salida. Los importes aplicados se conservan aunque cambie el precio actual. Promociones individuales por producto. Sugerencia contiene cantidad para reposición o precio para descuento. Campos de decisión pueden estar vacíos mientras esté pendiente.
