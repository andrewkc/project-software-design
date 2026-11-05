# Actores y trabajadores

## Actores

| Código | Actor | Interacción |
|---|---|---|
| AN-01 | Administrador de la app | Mantiene cuentas, roles y estado de acceso. |
| AN-02 | Jefe de bodega | Gestiona establecimiento/empleados, supervisa y decide precios, promociones y reposiciones. |
| AN-03 | Empleado de bodega | Registra entradas/salidas y consulta existencias/alertas. |

No se incluye proveedor. La IA no es actor autorizador. El jefe puede ejecutar funciones del empleado sin segunda cuenta.

## Trabajadores

| Código | Trabajador | Responsabilidad | Casos |
|---|---|---|---|
| TN-01 | Administrador de la app | Cuentas y accesos generales | CU-01 |
| TN-02 | Jefe de bodega | Bodega, catálogo, empleados, supervisión, precios y sugerencias; también operaciones del empleado | CU-02 a CU-09 |
| TN-03 | Empleado de bodega | Entradas, salidas, existencias y vencimientos | CU-04, CU-05, CU-06 |

Cada bodega tiene un jefe y puede tener varios empleados. Inicialmente, jefe o empleado pertenece a una sola bodega. El administrador no necesita asignación a establecimiento.
