# Reglas de negocio

| Código | Regla | Tipo | Casos |
|---|---|---|---|
| RN-01 | Administrador gestiona cuentas y accesos. | Autorización | CU-01 |
| RN-02 | Jefe gestiona bodega y empleados y realiza operaciones del empleado. Cada empleado accede solo a su bodega. | Autorización | CU-02…CU-09 |
| RN-03 | Toda entrada/salida indica productos, lotes, cantidades positivas y responsable. | Validación | CU-04, CU-05, CU-07 |
| RN-04 | Salida no supera existencias; al confirmar stock se descuenta una sola vez. | Restricción | CU-05, CU-06 |
| RN-05 | Total venta = suma de cantidad × precio aplicado por producto. | Cálculo | CU-05 |
| RN-06 | Productos vencidos o deteriorados no se venden; retiro es merma. | Restricción | CU-05, CU-06, CU-08 |
| RN-07 | Solo jefe modifica precios y aprueba descuentos/promociones. | Autorización | CU-02, CU-08 |
| RN-08 | Sugerencias IA requieren aprobación del jefe; puede modificarlas o rechazarlas. Reposición aprobada no genera compra. | Autorización | CU-08, CU-09 |
| RN-09 | Promoción: precio positivo menor al regular; fecha fin posterior a inicio; aplica durante vigencia y con stock apto. | Validación | CU-05, CU-08 |
