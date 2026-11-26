# ADR-010: Descuento generado para todas las bodegas

**Estado:** Solicitado explícitamente por el producto el 2026-11-26. Implementado como propuesta en `apps/backend`. Pendiente de rebuild/push y validación en el catálogo desplegado.

**Fecha:** 2026-11-26

## Contexto

`ensure_storefront_offers()` publicaba en `Oferta` los productos elegibles de todas las bodegas, pero aplicaba el 20% de descuento únicamente a un subconjunto fijo de nombres de `Bodega San Martín`. El resto se publicaba a precio real. En la tienda, el Inicio y la vista de bodega mostraban muchas filas con descuento de San Martín y, para una bodega nueva como `Bodega San Pedro`, una sola fila sin descuento. El usuario pidió que se generen ofertas para los productos de **todas** las tiendas.

No hay ningún endpoint en el MVP que permita a un jefe crear una promoción: todas las filas de `Oferta` existentes provienen de `ensure_storefront_offers()` o del seed local opcional. Por eso era seguro regenerarlas sin pisar una decisión humana.

## Decisión

1. `STOREFRONT_DISCOUNT_RATE = Decimal("0.8")` se aplica a **todo** producto activo, no bloqueado, con `stock > 0`, `precio_venta > 0` y `fecha_vencimiento > CURRENT_DATE`, en **cualquier** bodega.
2. Se agrega `Oferta.es_generada BOOLEAN NOT NULL DEFAULT TRUE` en `database.sql` y una migración `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` en `ensure_schema()`. Las filas antiguas quedan marcadas como generadas, por lo que la primera lectura del catálogo las convierte a precio con descuento sin necesidad de borrar datos.
3. `ensure_storefront_offers()` actualiza el precio de las filas generadas cuando cambia `precio_venta`, y reactiva las que hubieran vencido en la ventana de vigencia. Nunca toca una fila con `es_generada = FALSE`: esa marca queda reservada para promociones aprobadas por el jefe si se agregan en el futuro.
4. El descuento es una regla determinista del prototipo, no una sugerencia ni una aprobación de IA. La IA sigue sin aprobar promociones ni modificar inventario.
5. `/customer/offers?store_id=…&page=N` mantiene el contrato: primero las ofertas vigentes y después 9 productos sin descuento por página. Como ahora casi todas las filas son ofertas, la sección «Productos en stock» queda vacía salvo que exista una promoción aprobada a precio real.

## Alternativas consideradas

- **Mantener el subconjunto fijo y agregar nombres nuevos:** se descartó porque dependería de comparar cadenas y no cubriría productos registrados después del despliegue.
- **Calcular el descuento solo al leer, sin filas en `Oferta`:** se descartó porque `POST /customer/orders` valida `offer_id` contra la tabla `Oferta`; haría falta cambiar el contrato de compra.
- **Borrar y reinsertar todas las ofertas:** se descartó porque destruiría identificadores referenciados por `DetalleCompra`. Se prefiere `UPDATE` sobre la misma fila.

## Consecuencias

- El precio cobrado por `POST /customer/orders` baja 20% para esos productos: `o.precio_oferta` alimenta `DetalleCompra.precio_unitario` y el total.
- La lectura del catálogo hace escrituras condicionales (`UPDATE ... WHERE ... IS DISTINCT FROM ...`) bajo un lock advisory; solo escribe cuando el precio o el estado cambiaron.
- Los productos con vencimiento pasado o sin fecha siguen sin publicarse por RN-05. La inclusión de los que no tienen fecha registrada queda como pregunta abierta, no se resuelve aquí.
- No se afirma que esto reduzca pérdidas: es una regla comercial del prototipo, no un resultado validado.

## Trazabilidad

- Solicitud del producto: «Yo quiero que se generé ofertas a los productos de todas las tiendas» (2026-11-26).
- Implementación: `apps/backend/database.py`, `apps/database/database.sql`, `apps/backend/routers/customer.py`.
- Contrato estático: `tests/test_customer_contract.py`.
- Especificación: [cliente-tienda/spec.md](../../05-specifications/cliente-tienda/spec.md) y [backend/README.md](../../../apps/backend/README.md).
