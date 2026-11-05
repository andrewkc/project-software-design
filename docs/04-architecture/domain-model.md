# Modelo de dominio conceptual

El diagrama de clases es conceptual: no define tablas, claves foráneas, tipos SQL ni tecnología.

El stock de un producto es la suma de cantidades disponibles de sus lotes. Cada detalle corresponde a un lote. Ventas con varios lotes generan varias líneas. Los importes históricos se conservan aunque cambie el precio del producto. Promociones individuales por producto. Sugerencias contienen cantidad de reposición o precio de descuento; campos de decisión pueden estar vacíos mientras pendientes.

**Revisión necesaria:** las multiplicidades del diagrama deben reconciliarse con el texto de asignación de personal y autorización del jefe. No cambiar sin decisión documentada.
