# ADR-003: Backend del primer corte

**Estado:** Aprobado por el usuario para el primer corte de `apps/backend`. Decisiones de alcance limitado; no constituyen la arquitectura definitiva de producción.

## Contexto

`apps/backend` era un archivo vacío. Los documentos de negocio no definen stack, API, autenticación ni persistencia, y el plan de implementación exige registrar estas decisiones antes de escribir código. ADR-002 indica que en producción SQLite debe estar en el servidor y las contraseñas deben hashearse.

## Decisión

- Framework: FastAPI, con Pydantic para validación y OpenAPI automático.
- Persistencia: SQLite local en un archivo configurable por `BODEGA_DB_PATH`. Migración posterior a PostgreSQL prevista, no implementada.
- Contraseñas: hash con `passlib[bcrypt]`. Ninguna contraseña se guarda en texto plano en el servidor.
- Autenticación: token opaco generado con `secrets.token_urlsafe`, guardado en la tabla `sessions` y enviado como `Bearer`. La revocación de una cuenta invalida sus sesiones.
- Alcance del primer corte: autenticación, perfiles de jefe y empleado, productos y movimientos. El rol administrador (CU-01) queda fuera, en línea con ADR-001.
- Aislamiento: cada petición opera sobre la bodega (`store`) del perfil autenticado.
- Reglas aplicadas: RN-03 a RN-06, RN-10 y RN-11, y convenciones de ADR-001 sobre propiedad, bloqueo, desactivación y revocación.

## Consecuencias

- El contrato HTTP es nuevo y no estaba en los documentos de negocio. Se deriva de los casos de uso y se considera propuesto hasta su revisión.
- `products.stock` se mantiene como valor consultable y se actualiza en la misma transacción que los lotes. Las ediciones directas de stock generan un movimiento de ajuste sin lote, porque el lote de ese ajuste sigue siendo la pregunta abierta 11.
- No se modelan aún estados de deterioro, catálogos de estado, moneda, precisión, unidades fraccionarias, selección FIFO/FEFO ni umbral de vencimiento. Permanecen como preguntas abiertas.
- La asignación de roles y la pertenencia a bodega se toman del perfil autenticado; no se confía en campos enviados por el cliente.
- Este backend no está conectado todavía a `operations-web`, que sigue usando su persistencia local.

## Trazabilidad

RN-01, RN-02, RN-03, RN-04, RN-05, RN-06, RN-10, RN-11 · RF-15, RF-16, RF-17, RF-18, RF-19, RF-23 · CU-01 a CU-07 · ADR-001, ADR-002 · Preguntas abiertas 3, 4, 11, 12, 13.
