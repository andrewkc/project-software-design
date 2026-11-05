# Entidades del negocio

| Código | Entidad | Atributos principales |
|---|---|---|
| EN-01 | Cuenta de usuario | idCuenta, nombre, correo, rol, estado |
| EN-02 | Bodega | idBodega, nombre, dirección, ubicación, presupuestoReposicion |
| EN-03 | Producto | idProducto, nombre, categoría, unidadMedida, precioVenta, estado |
| EN-04 | Lote | idLote, fechaIngreso, fechaVencimiento opcional, cantidadDisponible, costoUnitario |
| EN-05 | Movimiento de inventario | idMovimiento, fechaHora, tipo, motivo, total opcional |
| EN-06 | Detalle de movimiento | idDetalle, cantidad, importeUnitario opcional, subtotal opcional |
| EN-07 | Promoción | idPromocion, precioPromocional, fechaInicio, fechaFin, estado |
| EN-08 | Sugerencia de IA | idSugerencia, fechaGeneracion, tipo, cantidadSugerida/precioSugerido, justificación, estadoDecision, fechaDecision, cantidadAprobada/precioAprobado |

## Semántica
Stock = suma de cantidades disponibles de lotes. Cada detalle corresponde a un lote. Una venta que usa varios lotes genera varias líneas en una salida. Los importes aplicados se conservan aunque cambie el precio actual. Promociones individuales por producto. Sugerencia contiene cantidad para reposición o precio para descuento. Campos de decisión pueden estar vacíos mientras esté pendiente.
