# ADR-001 — Roles, propiedad de filas y candado de edición

**Estado:** Propuesto — aprobado por el usuario para su implementación en el prototipo `apps/operations-web`. Requiere reflejo en los documentos de negocio antes de considerarlo confirmado en el entregable.

## Contexto

Los documentos iniciales definen:

- AN-01/TN-01 “Administrador de la app” (CU-01, RN-01, RF-01) como actor de plataforma.
- CU-03 indicaba que, si la cuenta de empleado no existía, el administrador debía crearla mediante CU-01.
- RN-07 reservaba al jefe la modificación de precios.
- EN-03 (Producto) no registraba autoría ni bloqueo de edición.

El usuario precisó que ese “administrador” es personal interno de BodeSmart y no debe crear empleados de cada bodega. Además requirió que el jefe cree las cuentas de sus empleados, que el empleado solo edite las filas que él creó y que el jefe pueda bloquear filas para que solo él las edite.

## Decisión

1. El jefe crea, retira y bloquea el acceso de los empleados de **su** bodega. El administrador de plataforma queda fuera de este flujo en el MVP.
2. EN-03 incorpora `creadoPor` (EN-01), `bloqueado` y `bloqueadoPor`. Las filas de muestra iniciales se consideran creadas por el jefe.
3. Regla de edición:
   - Jefe: edita **todas** las filas, incluidas las bloqueadas; puede bloquear/desbloquear y desactivar/reactivar.
   - Empleado: edita **solo** las filas activas, no bloqueadas y cuyo `creadoPor` sea su `idCuenta`. Incluye precio y stock, según decisión del usuario.
   - Otro empleado: solo lectura.
4. El empleado **no elimina ni desactiva** filas. La acción del jefe pasa de “Eliminar” a **“Desactivar”**, conservando la fila y su historial (EN-03.estado).
5. Toda edición que cambie el stock genera un movimiento de ajuste en `bodega-movements` con responsable, producto, cantidades anterior/nueva, motivo y fecha. Queda pendiente definir el lote de este ajuste (pregunta abierta 11).
6. El jefe genera automáticamente la **contraseña inicial** de cada cuenta de empleado y entrega las credenciales. El cambio de contraseña por parte del empleado es opcional, no obligatorio. En el prototipo se guarda en texto plano en `localStorage`; en producción debe almacenarse hasheada y entregarse por un canal seguro.
7. "Eliminar" una cuenta significa **revocar el acceso**: la cuenta queda inactiva, no puede iniciar sesión y se conserva en la lista de revocados. Los movimientos y filas mantienen el responsable. Las filas creadas por ese empleado se bloquean automáticamente y solo el jefe puede editarlas.

## Consecuencias

- RN-07 se ajusta: el precio ya no es exclusivo del jefe en filas propias del empleado; la restricción pasa a estar ligada a la propiedad y al candado.
- Se añaden RN-10 (propiedad de filas) y RN-11 (candado).
- RF-01, RF-03 y RF-11 deben reflejar el nuevo reparto de responsabilidades.
- El prototipo necesita `role` e `idCuenta` en la cuenta activa; las cuentas sin rol existentes se tratan como jefe para no romper el estado guardado.
- La trazabilidad de ajustes de stock se guarda localmente; al existir movimientos reales (CU-04/CU-05) debe unificarse con EN-05/EN-06.

## Trazabilidad

CU-01, CU-02, CU-03, CU-07 · EN-01, EN-03, EN-05, EN-06 · RN-01, RN-02, RN-03, RN-04, RN-07, RN-10, RN-11 · RF-01, RF-03, RF-11 · Preguntas abiertas 5, 11, 21.
