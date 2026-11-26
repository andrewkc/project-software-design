# Alcance del MVP

## Incluido
Gestión de cuentas; bodega y catálogo; empleados; entradas; salidas por venta/merma; inventario y vencimientos; supervisión; precios y promociones; sugerencias IA para reposición/descuentos sujetas a decisión del jefe.

## Ampliación aprobada para la tienda pública

El equipo solicitó integrar `customer-web` con la lógica de compra de la rama
`avance-M`. El comprador puede consultar ofertas de varias bodegas, registrar
su cuenta, preparar una cesta de una sola bodega, reservar existencias diez
minutos, pagar en una simulación local o mediante Mercado Pago de prueba y
consultar sus pedidos. El recojo es informativo. Esta ampliación sustituye la
exclusión anterior de compradores y pagos de prueba.

## Excluido
Proveedores, pagos con dinero real, facturación electrónica, entregas, contabilidad,
registro por voz/fotografía y estimación de vida útil mediante IA.

## Límites
Una entrada registra mercadería ya recibida. Aprobar reposición es referencia interna, no pedido ni cambio de stock. Las sugerencias no se aplican solas. Los precios/promociones son de uso interno en ventas presenciales. Sin datos suficientes, inventario y consultas básicas siguen disponibles sin mostrar recomendaciones como validadas.
