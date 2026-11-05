# Constitución del proyecto

**Estado:** principios derivados del entregable inicial; las convenciones de ingeniería requieren ratificación del equipo.

## Principios del producto
1. Aplicación interna para bodegas/minimarkets.
2. Simplicidad y rapidez de registro son necesidades identificadas en entrevistas.
3. Inventario por lotes y movimientos.
4. Cada movimiento conserva responsable.
5. El jefe controla empleados, precios, promociones y decisiones de reposición.
6. IA como apoyo, nunca como autoridad.
7. Las operaciones confirmadas preservan consistencia de inventario.

## Principios de ingeniería propuestos
- Documentar y versionar decisiones junto al código.
- Trabajar incrementalmente por funcionalidad.
- Revisar criterios de aceptación antes de implementar.
- Registrar decisiones técnicas relevantes en ADR.
- Mantener cambios pequeños y trazables.

## Restricciones confirmadas
Tres roles; jefe hereda capacidades del empleado; empleado limitado a su bodega; stock suma lotes; salidas limitadas al stock y descontadas una sola vez; no vender vencidos/deteriorados; promoción con precio positivo inferior al regular y fin posterior al inicio; aprobación de reposición no genera compra ni modifica stock.

## Fuera del MVP
Proveedores, pasarelas de pago, facturación electrónica, entregas, contabilidad, registro automático por voz/fotografía y estimación de vida útil por IA.
