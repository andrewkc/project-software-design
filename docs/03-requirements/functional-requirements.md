# Requisitos funcionales iniciales

**Derivados de casos de uso; revisar y convertir en criterios verificables.**

| ID | Requisito | Trazabilidad |
|---|---|---|
| RF-01 | Administrador crea, actualiza, activa y desactiva cuentas. | CU-01, RN-01 |
| RF-02 | Jefe mantiene datos de su bodega y catálogo. | CU-02, RN-02 |
| RF-03 | Jefe incorpora/retira empleados conservando registros históricos. | CU-03 |
| RF-04 | Registrar entradas por producto, lote, cantidad, costo y vencimiento cuando aplique. | CU-04, RN-03 |
| RF-05 | Registrar salidas por venta o merma. | CU-05 |
| RF-06 | Impedir salidas superiores al stock y descontar una sola vez. | CU-05, RN-04 |
| RF-07 | Calcular total con cantidad y precio aplicado. | CU-05, RN-05 |
| RF-08 | Impedir venta de productos vencidos/deteriorados. | CU-05, RN-06 |
| RF-09 | Consultar existencias por producto/lote y vencimientos registrados. | CU-06 |
| RF-10 | Jefe consulta movimientos y responsables sin alterarlos. | CU-07 |
| RF-11 | Jefe modifica precios y gestiona promociones. | CU-08, RN-07, RN-09 |
| RF-12 | Jefe revisa, modifica, aprueba o rechaza sugerencias de descuento. | CU-08, RN-08 |
| RF-13 | Jefe revisa, modifica, aprueba o rechaza sugerencias de reposición. | CU-09, RN-08 |
| RF-14 | Aprobar reposición no genera compra ni modifica inventario. | CU-09, RN-08 |
| RF-15 | El jefe crea cuentas de empleado con contraseña inicial generada, entrega credenciales y revoca accesos conservando el historial. | CU-03, RN-02, ADR-001 (propuesto) |
| RF-16 | El empleado edita solo filas activas, no bloqueadas y creadas por él; no elimina ni desactiva. | CU-02, RN-10, ADR-001 (propuesto) |
| RF-17 | El jefe bloquea/desbloquea filas; una fila bloqueada solo la edita el jefe. | CU-02, RN-11, ADR-001 (propuesto) |
| RF-18 | El jefe desactiva productos conservando historial; un ajuste directo de stock registra responsable y valores anterior/nuevo. | CU-02, CU-07, RN-03, RN-11, ADR-001 (propuesto) |
| RF-19 | Los perfiles se persisten en SQLite: el login verifica correo, contraseña y estado; el registro y el alta de empleados insertan un registro único por correo. | CU-01, CU-03, ADR-002 (propuesto) |
| RF-20 | La interfaz adapta el lenguaje al rol: el jefe ve referencias a su bodega/inventario; el empleado ve la bodega asignada y el inventario de la bodega, sin presentarse como propietario. | CU-02, CU-03, RN-02, RN-10, ADR-001 (propuesto) |
| RF-21 | Junto al avatar circular de perfil se muestra siempre primer nombre y primer apellido, sin importar el rol; el nombre completo queda disponible en la página de perfil. | CU-01, CU-03, EN-01, ADR-001 (propuesto) |
| RF-22 | El inventario muestra el ID de cada fila y el autor como "Agregado por usted" o "Agregado por <nombre corto>"; el registro permite elegir el emoji del producto en cualquier modo. | CU-02, CU-04, EN-03, RN-03, RN-10, ADR-001 (propuesto) |
