# Propuesta de backlog técnico y tablero Kanban

**Estado:** Propuesto; requiere revisión y aprobación del equipo.

**Propósito:** convertir el modelo SDD existente en tareas pequeñas, verificables y asignables a tres developers, manteniendo trazabilidad y reduciendo conflictos de archivos.

## 1. Lectura actual del proyecto

### Confirmado

- El MVP cubre CU-01 a CU-09, EN-01 a EN-08 y RN-01 a RN-09.
- El jefe puede ejecutar operaciones del empleado y el empleado solo puede acceder a su bodega.
- Las entradas y salidas deben identificar responsable, productos, lotes y cantidades positivas.
- Una salida no puede superar el stock, debe descontarlo una sola vez y no puede vender productos vencidos o deteriorados.
- Solo el jefe modifica precios y aprueba promociones o sugerencias.
- La IA es apoyo para decisiones: nunca aprueba sola, genera compras ni modifica inventario automáticamente.

### Observado en el repositorio

- [App.jsx](../../apps/frontend/src/App.jsx) concentra la interfaz y el estado de una demo en un solo módulo, con datos iniciales y `localStorage`.
- [package.json](../../apps/frontend/package.json) muestra un frontend React/Vite existente.
- [schema.sql](../../apps/database/schema.sql) solo contiene un comentario; no hay esquema del dominio implementado.
- [01_create_database.sql](../../apps/database/01_create_database.sql) contiene una tabla `users` de ejemplo, todavía no trazada a EN-01.
- [main.py](../../apps/backend/main.py) contiene un ejercicio de medición de palabras de Pauli de tres qubits, no una API del dominio.
- [tests/main.py](../../tests/main.py) no constituye todavía una estrategia de pruebas del MVP.

Estos hallazgos describen el estado del repositorio; no significan que el producto esté implementado.

### Pendiente antes de cerrar el plan técnico

- Arquitectura, stack y contrato frontend/backend.
- Persistencia, autenticación, autorización y sesiones.
- Moneda, precisión, unidades y cantidades fraccionarias.
- Estados de cuentas, productos, promociones y sugerencias.
- Selección de lote cuando existen varios y umbral de “próximo a vencer”.
- Comportamiento de salida parcialmente inválida, cambios de precio antes de confirmar y promociones simultáneas.
- Dispositivos, navegadores, conectividad/offline, backup, privacidad, retención y observabilidad.
- Historial mínimo, método y evaluación de las sugerencias de IA.

No se deben resolver estos puntos implícitamente dentro de una tarea de código. Deben convertirse en decisión aprobada, ADR o pregunta abierta.

## 2. Cómo organizar el tablero

### Columnas

1. `Preguntas / por decidir`
2. `Ready — spec revisada`
3. `En progreso`
4. `En revisión`
5. `Validación`
6. `Done — código + pruebas + docs`

Una tarjeta no entra en `Ready` si no tiene objetivo, alcance, trazabilidad, criterios de aceptación, dependencia, archivos de propiedad y preguntas pendientes identificadas.

### Etiquetas recomendadas

`decisión`, `contrato`, `backend`, `frontend`, `database`, `test`, `docs`, `seguridad`, `bloqueado`.

### Regla de propiedad para evitar solapamientos

Cada tarjeta debe declarar un propietario principal y una superficie de archivos. Los cambios compartidos se hacen solo mediante una tarjeta de contrato o por el propietario de esa carpeta. Los demás developers consumen el contrato sin editarlo. Un PR no debe mezclar dos funcionalidades salvo que la dependencia esté documentada.

### ¿Por frontend/backend o por casos de uso?

#### Opción A: dos developers frontend y uno backend

Es más sencilla para repartir especialidades, pero tiene tres riesgos en este proyecto:

- el developer backend se convierte en cuello de botella para CU-01..CU-09;
- los dos developers frontend pueden modificar los mismos componentes, estados y navegación de [App.jsx](../../apps/frontend/src/App.jsx);
- se puede avanzar visualmente sin validar pronto RN-02, RN-03, RN-04 y RN-08, que son las reglas de mayor riesgo.

Esta opción funciona mejor cuando ya existe un backend estable, contratos versionados, autenticación resuelta y una UI modular. El repositorio actual todavía no está en ese punto.

#### Opción B: dividir directamente por cada caso de uso

Mejora la trazabilidad SDD y permite entregar incrementos verticales, pero dividir CU-04, CU-05 y CU-06 como tareas completamente independientes duplicaría la lógica de stock. También ocurriría algo similar si cada caso implementa por separado permisos, responsables, lotes o promoción.

#### Recomendación propuesta: bloques verticales por casos de uso

Usar tres propietarios de bloque, como en las secciones siguientes:

- Dev A: CU-01..CU-03, acceso, bodega, catálogo y empleados.
- Dev B: CU-04..CU-06, movimientos, stock, lotes, salidas e inventario.
- Dev C: CU-07..CU-09, supervisión, precios, promociones y sugerencias.

Cada propietario trabaja en la parte de backend, frontend y pruebas de su bloque, dentro de sus carpetas. El equipo define primero los contratos comunes T-02, T-03 y T-04. Así se conserva la trazabilidad por CU/RF/RN sin convertir cada caso en una miniaplicación aislada.

La división frontend/backend puede usarse como apoyo temporal: quien tenga mayor experiencia backend puede custodiar los contratos y la integración, mientras los otros dos implementan las pantallas de sus bloques. Esa función de coordinación no debe convertirse en propiedad exclusiva de todo el backend, porque retrasaría los tres bloques.

#### Regla especial para inventario

CU-04, CU-05 y CU-06 deben pertenecer al mismo bloque y compartir el mismo núcleo de movimientos/stock. Se pueden separar en tarjetas, especificaciones y PRs, pero no en implementaciones independientes de la invariancia de stock. Esto protege RN-03, RN-04, RN-05 y RN-06.

## 3. Orden de trabajo recomendado

```text
Decisiones técnicas y de negocio
          ↓
Contratos + estructura modular + datos de prueba
          ↓
CU-01..03       CU-04..06       CU-07..09
 acceso         inventario      supervisión/decisiones
          \          |          /
             integración y validación
```

La división por bloques permite trabajar en paralelo después del contrato común. CU-04, CU-05 y CU-06 deben compartir un único servicio de movimientos/stock; no deben implementarse como tres descuentos de stock independientes.

## 4. Tarjetas iniciales para Trello

Las siguientes tarjetas son una propuesta de Tasks. El tamaño objetivo es una unidad que pueda revisarse y validarse de forma independiente.

### Fase 0 — decisiones y contrato común

| ID | Tarjeta | Responsable sugerido | Depende de | Trazabilidad / salida verificable |
|---|---|---|---|---|
| T-00 | Resolver decisiones bloqueantes del MVP | Equipo | — | Actualiza [open-questions.md](../03-requirements/open-questions.md) o crea ADR; no deja decisiones silenciosas. |
| T-01 | Aprobar arquitectura y límites de módulos | Equipo | T-00 | ADR aprobado; define interfaces, no tablas o tecnologías inventadas. |
| T-02 | Definir contrato de identidad, bodega y error | Dev A | T-01 | Contrato versionado para EN-01/EN-02, roles AN-01..AN-03 y aislamiento RN-01/RN-02. |
| T-03 | Definir contrato de producto, lote y movimiento | Dev B | T-01 | Contrato versionado para EN-03..EN-06 y RN-03..RN-06. |
| T-04 | Definir contrato de promoción y sugerencia | Dev C | T-01 | Contrato versionado para EN-07/EN-08 y RN-07..RN-09; estados pendientes explícitos. |
| T-05 | Crear estructura modular y comandos de prueba | Dev A | T-02..T-04 | App arranca; módulos separados por feature; pruebas ejecutables documentadas. |
| T-06 | Crear fixtures mínimos trazables | Dev B | T-03 | Datos de prueba para bodega, jefe, empleado, productos, lotes y movimientos; sin datos reales. |
| T-07 | Preparar plantilla de spec, plan y tasks por feature | Dev C | T-01 | Cada bloque de CU tiene carpeta y documentos desde la plantilla SDD. |

### Bloque A — cuentas, bodega y empleados (CU-01..CU-03)

**Propietario:** Dev A. **Superficie:** módulo de identidad/organización y sus pruebas; no modificar el núcleo de inventario.

| ID | Tarjeta | Depende de | Aceptación mínima |
|---|---|---|---|
| T-10 | Especificar CU-01 | T-02, T-07 | RF-01, RN-01, excepciones y escenarios de permisos documentados. |
| T-11 | Implementar administración de cuentas | T-10, T-05 | Crear, modificar, activar y desactivar con validaciones; correo duplicado y sin permiso no guardan. |
| T-12 | Especificar CU-02 y CU-03 | T-10 | Incluye aislamiento de bodega, catálogo y conservación histórica. |
| T-13 | Implementar bodega y catálogo | T-12 | Jefe modifica solo su bodega; precio no positivo y otra bodega se rechazan. |
| T-14 | Implementar asignación y retiro de empleados | T-12, T-11 | Solo cuenta activa con rol empleado y sin otra bodega; retiro no borra historial. |
| T-15 | Probar permisos y aislamiento | T-11, T-13, T-14 | Casos AN-01..AN-03 y RN-01/RN-02 cubiertos; empleado no entra a CU-07..CU-09. |

### Bloque B — entradas, salidas e inventario (CU-04..CU-06)

**Propietario:** Dev B. **Superficie:** módulo de inventario/movimientos y sus pruebas; Dev A expone identidad, Dev C consume consultas.

| ID | Tarjeta | Depende de | Aceptación mínima |
|---|---|---|---|
| T-20 | Especificar CU-04 | T-03, T-06, T-07 | RF-04 y RN-03 con lote, responsable, cantidad positiva y cancelación sin cambio. |
| T-21 | Implementar registro transaccional de entradas | T-20, T-05 | Guarda movimiento/detalles y aumenta stock de lotes una vez; producto inexistente no guarda. |
| T-22 | Especificar CU-05 | T-20 | Casos de venta y merma, revalidación al confirmar y rechazo de operación parcial. |
| T-23 | Implementar salida atómica y cálculo de venta | T-22, T-21 | No supera stock; descuenta una vez; conserva responsable/lote/precio aplicado; RN-04..RN-06 y RN-09. |
| T-24 | Especificar e implementar CU-06 | T-21, T-23 | Consulta por producto/lote y vencimientos; respeta bodega; no inventa umbral pendiente. |
| T-25 | Probar invariantes de stock | T-21, T-23, T-24 | Cantidades positivas, stock por suma de lotes, doble confirmación y concurrencia definida por el ADR. |

### Bloque C — supervisión, precios y sugerencias (CU-07..CU-09)

**Propietario:** Dev C. **Superficie:** módulo de supervisión/decisiones y sus pruebas; no editar la lógica de descuento de stock.

| ID | Tarjeta | Depende de | Aceptación mínima |
|---|---|---|---|
| T-30 | Especificar CU-07 | T-03, T-07 | Filtros por empleado/periodo y detalle inmutable con responsable, lotes, cantidades e importes. |
| T-31 | Implementar consulta de movimientos y auditoría de lectura | T-30, T-21, T-23 | Jefe ve registros de su bodega; empleado no accede; ningún endpoint altera movimientos. |
| T-32 | Especificar CU-08 | T-04, T-07 | Precio/promoción manual y sugerida; RN-07/RN-09; cambios y aprobación quedan trazables. |
| T-33 | Implementar gestión de precios y promociones | T-32, T-24 | Solo jefe; precio positivo menor al regular, fechas válidas y stock apto; promoción desactivable. |
| T-34 | Especificar CU-09 y límites IA | T-04, T-07 | Historial insuficiente, indisponibilidad IA y decisión pendiente se comportan explícitamente. |
| T-35 | Implementar revisión de sugerencias | T-34, T-33 | Jefe puede modificar/aprobar/rechazar; reposición aprobada no compra ni cambia stock. |
| T-36 | Probar límites de IA y autorización | T-31, T-33, T-35 | IA no aprueba, compra ni modifica inventario; consultas básicas siguen disponibles sin IA. |

### Fase común — frontend, integración y validación

Estas tarjetas se asignan al developer que tenga disponibilidad, pero el propietario de cada módulo revisa sus cambios.

| ID | Tarjeta | Responsable sugerido | Depende de | Aceptación mínima |
|---|---|---|---|---|
| T-40 | Dividir el prototipo monolítico en shell, componentes y features | Dev A | T-05 | [App.jsx](../../apps/frontend/src/App.jsx) queda como composición; no se cambian reglas de negocio accidentalmente. |
| T-41 | Implementar navegación y estados de carga/error/vacío | Dev A | T-40, T-02 | UI no expone datos de otra bodega y maneja fallos sin inventar resultados. |
| T-42 | Integrar pantallas CU-01..CU-03 | Dev A | T-11, T-13, T-14, T-41 | Flujos de cuenta, bodega y empleados consumen contratos, no `localStorage` como persistencia final. |
| T-43 | Integrar pantallas CU-04..CU-06 | Dev B | T-21, T-23, T-24, T-41 | Entradas, salidas e inventario muestran resumen, errores y confirmación coherentes. |
| T-44 | Integrar pantallas CU-07..CU-09 | Dev C | T-31, T-33, T-35, T-41 | Supervisión, promociones y sugerencias respetan permisos y estados. |
| T-45 | Ejecutar pruebas de integración y E2E del MVP | Equipo | T-42..T-44 | Matriz CU/RF/RN con resultado, datos usados y defectos; sin afirmar impacto de negocio. |
| T-46 | Validar usabilidad y conectividad pendiente | Equipo | T-45 | Evidencia de validación; actualiza NFR y preguntas abiertas, sin inventar umbrales. |
| T-47 | Cerrar documentación y trazabilidad | Dev C | T-45, T-46 | Actualiza [traceability.md](../02-business/traceability.md), specs, [quality README](../06-quality/README.md) y ADRs. |

## 5. Protocolo SDD por tarjeta

Cada tarjeta de funcionalidad debe seguir este ciclo:

1. `Discover`: enlazar CU, evidencia y limitaciones.
2. `Specify`: completar `spec.md` con actores, permisos, flujos, reglas, excepciones, criterios y escenarios.
3. `Review`: otro developer revisa contradicciones y el equipo resuelve preguntas.
4. `Plan`: documentar interfaces, dependencias y superficie de archivos; las decisiones técnicas van a ADR.
5. `Tasks`: descomponer en tareas que produzcan una salida observable.
6. `Implement`: PR pequeño, con trazabilidad en descripción.
7. `Validate`: ejecutar pruebas y registrar resultados.
8. `Learn`: actualizar spec, preguntas, ADR, trazabilidad o calidad cuando se descubra algo nuevo.

## 6. Definition of Done

Una tarjeta está terminada solo si:

- cumple sus criterios de aceptación y conserva los identificadores CU/RF/RN/EN/AN/TN aplicables;
- tiene pruebas proporcionales al riesgo, especialmente para permisos y stock;
- no introduce proveedores, pagos, facturación, delivery, contabilidad, voz/fotografía operativa ni vida útil por IA;
- registra errores sin mutar stock parcialmente;
- actualiza la documentación afectada y enlaza cualquier decisión pendiente;
- fue revisada por el propietario de la superficie dependiente;
- el resultado distingue demo, prototipo y funcionalidad validada.

## 7. Actualización documental mínima

| Evento | Documento a actualizar |
|---|---|
| Decisión de alcance o contradicción | [open-questions.md](../03-requirements/open-questions.md), ADR si es técnica |
| Cambio de comportamiento | `docs/05-specifications/<feature>/spec.md` y requisito relacionado |
| Cambio de interfaces o módulos | `plan.md`, ADR y contexto/modelo si aplica |
| Nueva prueba o resultado | `tasks.md` y [docs/06-quality/README.md](../06-quality/README.md) |
| Cambio de relación CU/RF/RN/EN | [traceability.md](../02-business/traceability.md) |
| Descubrimiento durante implementación | spec, pregunta abierta o ADR; nunca solo el código |

## 8. Recomendación para la primera iteración

No repartir todavía T-11, T-21 y T-33 como implementación definitiva. Primero cerrar T-00/T-01 y revisar los contratos T-02/T-03/T-04. Después, el primer incremento vertical razonable es CU-01 + CU-02 + CU-03, seguido por CU-04 y CU-06; CU-05 debe entrar cuando la transacción atómica y sus pruebas estén listas. CU-08 y CU-09 deben esperar la definición de estados y del límite IA, aunque sus pantallas pueden diseñarse con datos explícitamente marcados como prototipo.

## 9. Backlog del Sprint 1

El backlog de producto propuesto para el primer sprint está en [sprint-01-product-backlog.md](./sprint-01-product-backlog.md). Se plantea como un sprint de fundación porque la arquitectura, los contratos y la estrategia de pruebas aún no están aprobados.
