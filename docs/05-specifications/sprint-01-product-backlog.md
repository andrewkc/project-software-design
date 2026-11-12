# Product backlog — Sprint 1

**Estado:** Propuesto; requiere validación del equipo.

**Duración y fechas:** pendientes. No se inventan fechas ni story points porque el equipo todavía no ha definido duración, capacidad ni criterio de estimación.

## Objetivo del sprint

Dejar aprobada y trazable la base necesaria para implementar el MVP por bloques de casos de uso, con contratos comunes y una estructura modular que permita trabajar a tres developers sin editar los mismos archivos.

## Resultado esperado

Al finalizar el sprint, el equipo debería poder demostrar:

- decisiones de alcance y arquitectura registradas;
- contratos iniciales para identidad, bodega, productos, lotes, movimientos, promociones y sugerencias;
- estructura modular preparada para CU-01..CU-09;
- criterios de aceptación y escenarios de prueba para los tres bloques;
- fixtures mínimos trazables;
- comandos de validación documentados y ejecutables;
- preguntas que sigan abiertas, claramente separadas de decisiones aprobadas.

Este sprint no acredita que el producto esté implementado ni que reduzca pérdidas.

## Product Backlog Items del sprint

| ID | Prioridad | Product Backlog Item | Valor para el producto | Trazabilidad | Propietario |
|---|---|---|---|---|---|
| PBI-01 | Must | Como equipo, queremos resolver las decisiones bloqueantes del MVP para que las funcionalidades no se implementen con supuestos contradictorios. | Reduce retrabajo y mantiene el alcance controlado. | CU-01..CU-09; EN-01..EN-08; RN-01..RN-09; preguntas 1..23 | Equipo |
| PBI-02 | Must | Como equipo, queremos aprobar los límites de módulos y contratos para que frontend, backend y pruebas puedan avanzar en paralelo. | Permite integración sin acoplamiento accidental. | AN-01..AN-03; TN-01..TN-03; ADR | Dev A + equipo |
| PBI-03 | Must | Como responsable de acceso, quiero especificar identidad, bodega y permisos para garantizar que cada empleado vea solo su bodega y que el jefe herede sus capacidades. | Protege RN-01 y RN-02. | CU-01..CU-03; RF-01..RF-03; EN-01..EN-02 | Dev A |
| PBI-04 | Must | Como responsable de inventario, quiero definir el contrato único de lotes y movimientos para que entradas, salidas e inventario conserven stock consistente. | Protege la regla crítica de stock y evita duplicar lógica. | CU-04..CU-06; RF-04..RF-09; RN-03..RN-06; EN-03..EN-06 | Dev B |
| PBI-05 | Should | Como responsable de decisiones, quiero definir el contrato de promociones y sugerencias para que la IA no apruebe ni modifique inventario por sí sola. | Protege RN-07..RN-09 y el límite del MVP. | CU-08..CU-09; RF-11..RF-14; EN-07..EN-08 | Dev C |
| PBI-06 | Must | Como developer, quiero una estructura modular y una base de pruebas para entregar cambios pequeños y verificables. | Hace operable el trabajo paralelo de los tres developers. | Constitución; docs/06-quality; T-05/T-06 | Dev A + Dev B |
| PBI-07 | Must | Como equipo, queremos especificaciones revisadas para los tres bloques funcionales para que cada implementación posterior tenga criterios verificables. | Convierte el modelo de negocio en trabajo implementable. | CU-01..CU-09; RF; RN; EN; AN; TN | Dev C + equipo |

## Criterios de aceptación del sprint

- [ ] Las preguntas bloqueantes se resolvieron o quedaron registradas como pendientes explícitas en [open-questions.md](../03-requirements/open-questions.md).
- [ ] Toda decisión técnica nueva tiene ADR aprobado o está marcada como propuesta; no se fija tecnología por costumbre.
- [ ] Los contratos definen entradas, salidas, errores, permisos y propietario de cada módulo.
- [ ] El contrato de movimientos representa responsable, producto, lote y cantidad positiva.
- [ ] El contrato de salida contempla no superar stock, descuento único, revalidación al confirmar y rechazo sin salida parcial.
- [ ] El contrato de venta conserva el precio aplicado y distingue venta de merma.
- [ ] El contrato de promociones contempla precio positivo menor al regular, vigencia y stock apto.
- [ ] El contrato de sugerencias deja explícito que aprobar reposición no genera compra ni modifica inventario.
- [ ] Existen fixtures para al menos una bodega, un jefe, un empleado, productos, lotes y movimientos; los datos están identificados como prueba.
- [ ] La estructura modular y los comandos de prueba están documentados y se ejecutan sin depender de la demo de [App.jsx](../../apps/frontend/src/App.jsx).
- [ ] Cada PBI tiene spec, plan o tarea relacionada y mantiene trazabilidad a CU/RF/RN/EN/AN/TN.

## Sprint backlog técnico

Estas tareas se derivan del backlog técnico existente. Son tarjetas sugeridas para Trello; el equipo debe confirmarlas durante la planificación.

### Trabajo común

| ID | Tarea | Responsable | Dependencia | Salida verificable |
|---|---|---|---|---|
| S1-T01 | Revisar y clasificar preguntas abiertas bloqueantes | Equipo | — | Lista de decisiones, pendientes y fuera de alcance; actualiza open questions. |
| S1-T02 | Aprobar límites de arquitectura y módulos | Equipo | S1-T01 | ADR o decisión aprobada con superficies de archivos y contratos. |
| S1-T03 | Definir estructura modular inicial | Dev A | S1-T02 | Carpetas/módulos de features y shell; [App.jsx](../../apps/frontend/src/App.jsx) no recibe nuevas reglas de negocio. |
| S1-T04 | Definir estrategia mínima de pruebas y comandos | Dev B | S1-T02 | Comandos documentados para pruebas de dominio, integración y frontend disponibles. |
| S1-T05 | Crear fixtures trazables | Dev B | S1-T02 | Fixtures reutilizables para los escenarios del sprint. |
| S1-T06 | Crear carpetas y documentos SDD de los tres bloques | Dev C | S1-T02 | `spec.md`, `plan.md` y `tasks.md` iniciales con estado Draft. |

### Bloque A — acceso y organización

| ID | Tarea | Responsable | Dependencia | Salida verificable |
|---|---|---|---|---|
| S1-A01 | Especificar CU-01 | Dev A | S1-T01, S1-T06 | Criterios para crear, modificar, activar/desactivar y rechazar acceso. |
| S1-A02 | Especificar CU-02 y CU-03 | Dev A | S1-A01 | Permisos de jefe, aislamiento y retiro sin borrar historial. |
| S1-A03 | Definir contrato de identidad/bodega/error | Dev A | S1-T02, S1-A02 | Contrato revisado para EN-01/EN-02, AN-01..AN-03 y RN-01/RN-02. |
| S1-A04 | Preparar escenarios de prueba de permisos | Dev A | S1-A03 | Casos permitidos y rechazados para jefe, empleado y administrador. |

### Bloque B — inventario y movimientos

| ID | Tarea | Responsable | Dependencia | Salida verificable |
|---|---|---|---|---|
| S1-B01 | Especificar CU-04 | Dev B | S1-T01, S1-T06 | Entrada con lote, responsable, cantidad positiva y cancelación sin stock alterado. |
| S1-B02 | Especificar CU-05 | Dev B | S1-B01 | Venta/merma, revalidación, rechazo de vencido/deteriorado y sin salida parcial. |
| S1-B03 | Especificar CU-06 | Dev B | S1-B01 | Consulta por producto/lote y alertas sin inventar umbral pendiente. |
| S1-B04 | Definir contrato único de movimiento/stock | Dev B | S1-T02, S1-B01..S1-B03 | Reglas RN-03..RN-06 expresadas en invariantes y escenarios. |
| S1-B05 | Preparar pruebas de invariantes de stock | Dev B | S1-B04, S1-T05 | Escenarios de doble confirmación, cantidad inválida, stock insuficiente y lotes múltiples. |

### Bloque C — supervisión y decisiones del jefe

| ID | Tarea | Responsable | Dependencia | Salida verificable |
|---|---|---|---|---|
| S1-C01 | Especificar CU-07 | Dev C | S1-T01, S1-T06 | Consulta de movimientos con responsable, lotes, cantidades e importes inmutables. |
| S1-C02 | Especificar CU-08 | Dev C | S1-T01 | Precio, promoción, vigencia, stock apto y aprobación exclusiva del jefe. |
| S1-C03 | Especificar CU-09 y límites IA | Dev C | S1-T01 | Aprobación/rechazo/modificación; sin compras ni mutaciones automáticas. |
| S1-C04 | Definir contrato de promoción/sugerencia | Dev C | S1-T02, S1-C02, S1-C03 | Estados, errores y decisión del jefe explícitos. |
| S1-C05 | Preparar pruebas de autorización y límites IA | Dev C | S1-C04, S1-T05 | Escenarios RN-07..RN-09 y disponibilidad de consultas sin IA. |

## Dependencias y paralelismo

```text
S1-T01 → S1-T02 → S1-T03 / S1-T04 / S1-T05 / S1-T06
                       │          │          │
                       ├── Bloque A: S1-A01..S1-A04
                       ├── Bloque B: S1-B01..S1-B05
                       └── Bloque C: S1-C01..S1-C05
```

Los bloques A, B y C pueden avanzar en paralelo después de S1-T02. Dev B mantiene la propiedad del núcleo de movimientos/stock; Dev C no debe modificar esa lógica para implementar supervisión o sugerencias.

## Fuera del Sprint 1

- Implementación completa de CU-01..CU-09.
- Integración de proveedores, pagos, facturación electrónica, delivery o contabilidad.
- Registro operativo por voz/fotografía.
- Estimación de vida útil mediante IA.
- Selección definitiva de proveedor/modelo de IA.
- Umbrales cuantitativos de rendimiento, disponibilidad, seguridad o conectividad no aprobados.
- Migración de datos reales.

## Revisión del sprint

La revisión debe mostrar documentos, contratos, fixtures y pruebas ejecutables. No debe presentarse una maqueta o un contrato como funcionalidad terminada. Las decisiones no resueltas pasan al siguiente backlog o permanecen como preguntas abiertas con responsable.

## Actualización documental al cerrar el sprint

- [implementation-backlog.md](./implementation-backlog.md): marcar tareas completadas y ajustar dependencias.
- [open-questions.md](../03-requirements/open-questions.md): retirar solo preguntas realmente resueltas o registrar la nueva decisión.
- [traceability.md](../02-business/traceability.md): actualizar relaciones CU/RF/RN/EN cuando se aprueben.
- [docs/06-quality/README.md](../06-quality/README.md): registrar estrategia y resultados de pruebas.
- `docs/04-architecture/decisions/`: agregar ADRs aprobados.
- `docs/05-specifications/<feature>/`: mover specs, planes y tareas de Draft a In Review o Approved según corresponda.
