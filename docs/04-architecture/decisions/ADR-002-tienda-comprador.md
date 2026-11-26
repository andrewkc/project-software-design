# ADR-002 — Tienda pública y compra de prueba

**Estado:** Aprobada para esta integración por solicitud del equipo.

El MVP anterior excluía compradores y pagos. El equipo cambió ese alcance y
pidió integrar la experiencia de comprador de `avance-M` en `main`, manteniendo
la apariencia de las pantallas actuales.

Se añade `customer-web` como tienda pública y rutas `/customer` en el backend
existente. La cesta pertenece a una sola bodega. El servidor valida precio,
vigencia y stock, congela el total y reserva existencias diez minutos. Solo
el pago simulado local o una aprobación de Mercado Pago de prueba comprobada
por el servidor descuenta inventario, una vez. El recojo es informativo.

La decisión conserva `ProductosBodega` como saldo compartido con la vista de
operaciones. Esta tabla representa un producto por bodega, no varios lotes.
Por ello el flujo del cliente queda integrado, pero la paridad de inventario
por múltiples lotes de `avance-M` requiere una adaptación posterior de la
vista de operaciones y la base. El pago real, reparto y administrador no son
parte de esta decisión.
