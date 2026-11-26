# ADR-008 — Alcance del panel administrativo sobre cuentas

**Estado:** Aprobado por el usuario en esta sesión. Registra un cambio de alcance respecto de ADR-001 para `apps/admin-web`; no elimina el flujo del jefe en `apps/operations-web`.

## Contexto

- CU-01 describe al administrador de plataforma como responsable de cuentas y accesos.
- ADR-001 decidió que, en el primer corte de `operations-web`, el jefe creaba y revocaba empleados y el administrador quedaba fuera de ese flujo.
- El usuario pidió implementar `admin-web` con secciones propias y extraer del backend de referencia los endpoints administrativos necesarios.
- El panel de referencia muestra altas, ediciones y bajas de todos los roles, pero incluye atajos de autenticación, pagos y datos sin trazabilidad que **no** se copiaron.
- Ante la contradicción, se preguntó al usuario si el admin debía gestionar también jefes y empleados. Respondió: **“Gestionar todos los roles (Recomendado)”**.
- Luego precisó una restricción de autoprotección: **una cuenta admin no puede borrar ni modificar cuentas de otros admins**.

## Decisión

1. `admin-web` permite al rol `admin` **listar, crear, editar y desactivar** cuentas de los cuatro roles locales: `admin`, `jefe`, `empleado` y `cliente`.
2. Un administrador **no puede editar ni desactivar la cuenta de otro administrador**. Solo puede editar la suya, y no puede desactivarla. El backend responde `403` para otro admin y `400` para la autodesactivación.
3. La baja sigue siendo una **desactivación lógica** (`estado = 'inactivo'`), nunca un borrado físico, para conservar historial y trazabilidad.
4. Los endpoints viven en un router aislado `/admin/...` y usan el mismo esquema Bearer que el backend actual. No se cambian los contratos de `/auth/*`, `/profiles/*` ni `/customer/*`.
5. El panel no consulta costos, ventas, márgenes ni precios. Los contadores del panel son solo cantidades de cuentas y bodegas.
6. La IA continúa siendo apoyo: no aprueba, no crea movimientos y no modifica inventario desde este panel.
7. Para la demo local se siembra una cuenta `admin@bodesmart.local` en `apps/database/seed.sql` con contraseña de prototipo; `ensure_schema()` la hashea con bcrypt en el arranque. No es una credencial de producción.

## Consecuencias

- ADR-001 punto 1 queda **superado únicamente para `admin-web`**: el jefe conserva en `operations-web` la gestión de empleados de su bodega.
- Se agregan las rutas `POST /admin/auth/login`, `GET /admin/me`, `GET /admin/users`, `POST /admin/users`, `GET /admin/stores`, `PATCH /admin/users/{uid}` y `DELETE /admin/users/{uid}`.
- `database.ensure_schema()` agrega de forma idempotente `Jefe.estado`, `Admin.estado`, `Admin.fecha_creacion`, `Admin.ultimo_acceso` y el índice único de correo insensible a mayúsculas; `email_exists()` pasa a considerar los cuatro roles para evitar correos duplicados entre plataformas.
- `Jefe.estado` se respeta en `/auth/login` y en `bodega_id_for()`: un jefe desactivado ya no puede iniciar sesión ni resolver su bodega.
- Las filas creadas por un empleado desactivado desde admin-web se bloquean igual que en la revocación hecha por el jefe, manteniendo coherencia con ADR-001.
- El frontend admin usa los tokens de `operations-web`: DM Sans/Manrope, `--font-scale: 1.4`, paleta `#397a55` / `#f7f8f3` / `#252c26`, sidebar, nav móvil, tarjetas, tabla, drawer, confirmación y toast.
- La tabla `Admin` ya existía en `database.sql`, pero no tenía código que la usara; ahora tiene un Propósito confirmado en el corte admin.

## Alternativas consideradas

- **Mantener ADR-001 sin cambios y limitar el admin a `admin`/`cliente`:** descartada por el usuario.
- **Copiar la autenticación por cookies/CSRF del proyecto de referencia:** descartada porque rompería el contrato Bearer actual de `operations-web` y `customer-web`.
- **Copiar `/auth/demo-admin`:** descartada; otorgaba ADMIN ante fallos de `/auth/me` y es un atajo solo demo.
- **Borrado físico:** descartado; las FKs de compras, pagos y productos creados darían pérdida de trazabilidad.

## Trazabilidad

CU-01 · EN-01, EN-02, EN-03 · RN-01, RN-02 · RF-01, RF-19 · AN-01, AN-03 · TN-01, TN-03 · ADR-001 (superado parcialmente) · Preguntas abiertas 19–21.
