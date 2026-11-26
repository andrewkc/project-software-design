# ADMIN-01 — Panel administrativo de cuentas y bodegas

**Estado:** Aceptado por el usuario el 2026-11-26 como ampliación confirmada del alcance. Prototipo implementado en backend, esquema/seed y frontend. **Pendiente:** ejecutar `pytest`, `npm run build`, reconstruir contenedores y validar en navegador con una cuenta admin.

## Identificador y trazabilidad

`ADMIN-01` es un identificador técnico incremental que amplía **CU-01** (administrar cuentas y accesos). Reutiliza **EN-01**, **EN-02**, **EN-03**, **AN-01/AN-03**, **TN-01/TN-03**, **RN-01/RN-02**, **RF-01/RF-19**. La decisión de alcance quedó registrada en **ADR-008**, que supera parcialmente **ADR-001** solo para `apps/admin-web`. No crea nuevas reglas numeradas ni amplía el MVP con proveedores, pagos reales, facturación, delivery, contabilidad ni IA que modifique inventario.

## Problema y objetivo

**Confirmado por el usuario:** quiere `admin-web` con la paleta y tipografía de `operations-web`, menú de administrador con secciones propias, perfil con rol `Admin`, y los endpoints admin que faltan en el backend actual, tomando como referencia el backend de otro checkout sin copiar sus atajos inseguros ni su alcance fuera del MVP.

**Confirmado durante la revisión:** el administrador gestiona **todos los roles**. Luego el usuario precisó que una cuenta admin **no puede borrar ni modificar cuentas de otros admins**.

**Derivado de la revisión:** el backend actual ya usa Bearer + `rol` en el token, así que el contrato admin se aísla en `/admin/*` para no romper jefe, empleado ni cliente. La tabla `Admin` existía en SQL pero no tenía código que la consumiera.

**Objetivo:** ofrecer una consola de plataforma para listar, crear, editar y desactivar cuentas, consultar bodegas y ver el perfil `Admin`, sin exponer contraseñas, costos, ventas ni márgenes.

## Alcance incluido / excluido

### Incluido

- Login admin con `POST /admin/auth/login`, token Bearer y `GET /admin/me`.
- `GET /admin/users` con los cuatro roles y `bodegaNombre`, `activo`, `creado`, `ultimoAcceso`; nunca `password`.
- `POST /admin/users` para crear cualquiera de los cuatro roles; jefe/empleado requieren bodega válida y el empleado requiere jefe activo en esa bodega.
- `PATCH /admin/users/{id}` y `DELETE /admin/users/{id}` con autoprotección entre administradores y baja lógica.
- `GET /admin/stores` para el listado de bodegas.
- Migraciones idempotentes en `database.ensure_schema()` y cuenta demo sembrada en `seed.sql`, hasheada en el arranque.
- UI con Panel, Cuentas, Bodegas y Perfil; tabla con búsqueda, rol, orden, drawer de alta/edición, confirmación de desactivación y toast.
- Misma paleta y escala tipográfica de `operations-web`, sidebar fija y bottom nav móvil.

### Excluido

- `/auth/demo-admin`, cookies/CSRF, checkout, pagos, chat, IA, voz, foto, escaneo y branding `Bodega Clara` del checkout de referencia.
- Costos, márgenes, precios, ventas, análisis de pérdidas ni métricas de efectividad comercial en el panel.
- Borrado físico de cuentas: se conserva historial con `estado = 'inactivo'`.
- Cambio de rol sobre una cuenta existente: se crea otra y se desactiva la anterior.
- Promociones, sugerencias o inventario gestionados desde admin-web.
- Despliegue real o afirmación de que el producto reduce pérdidas; las entrevistas son exploratorias.

## Actores y permisos

| Actor | Permiso |
|---|---|
| Admin (AN-01) | Gestiona cuentas de los cuatro roles y consulta bodegas. Puede editar su propia cuenta, pero no desactivarla. No puede editar ni desactivar a otro admin. |
| Jefe (AN-02) | No usa este panel en este corte; conserva `/profiles` en `operations-web`. Aparece en el listado admin. |
| Empleado (AN-03) | Aparece en el listado admin; sigue sujeto a la bodega asignada y a la revocación del jefe. |
| Cliente | Aparece en el listado admin; sigue usando `/customer/*`. |
| IA | No interviene en administración de cuentas ni aprueba cambios. |

## Precondiciones y postcondiciones

**Precondiciones:** token admin vigente; para crear jefe o empleado, bodega existente; para crear empleado, jefe activo en esa bodega; correo único entre los cuatro roles; contraseña de al menos 8 caracteres.

**Postcondiciones:** cuenta creada con contraseña bcrypt; cuenta editada sin exponer contraseñas; cuenta desactivada conservando filas e historial; si se desactiva un empleado, sus productos quedan bloqueados como en la revocación del jefe; ninguna otra cuenta admin resulta modificada.

## Flujo principal

1. El admin inicia sesión con su correo y contraseña; el backend valida `Admin.estado = 'activo'` y actualiza `ultimo_acceso`.
2. La app guarda el token en `bodesmart-admin-token` y carga `GET /admin/me`, `GET /admin/users` y `GET /admin/stores`.
3. En `Cuentas`, el admin busca, filtra por rol y abre el drawer para crear o editar.
4. Al guardar, el backend valida permisos, correo, bodega y contraseña; la app recarga el listado y muestra confirmación.
5. Para desactivar, la app pide confirmación y el backend marca `estado = 'inactivo'`; nunca elimina la fila.
6. En `Perfil`, la cuenta muestra rol `Admin` y la regla de autoprotección; el cierre de sesión descarta el token local.

## Alternativas y excepciones

| Situación | Comportamiento |
|---|---|
| Token ausente, inválido o de otro rol | `401`/`403`; la app vuelve al login. |
| Intento de editar/desactivar otro admin | `403` con mensaje explícito; los botones están deshabilitados en la UI. |
| Intento de desactivar la propia cuenta | `400`; el botón está deshabilitado en la UI. |
| Correo duplicado entre roles | `409`. |
| Bodega inexistente o sin jefe activo para empleado | `404`/`409`. |
| Contraseña corta | `400`. |
| Cambio de `rol` en PATCH | `400`; el rol no se cambia sobre la misma cuenta. |
| Base creada antes del seed admin | `ensure_demo_admin()` inserta la cuenta demo si no existe; `ensure_schema()` agrega columnas e índices. |

## Reglas de negocio

- **RN-01/RN-02:** un administrador puede operar cuentas de plataforma; el jefe mantiene su autoridad sobre la bodega en `operations-web`.
- **RN-03:** las altas capturan nombres y apellidos; contraseñas positivas y hasheadas, nunca devueltas al navegador.
- **Autoprotección ADMIN-01:** otro admin no es editable ni desactivable; la propia cuenta no se desactiva.
- **Baja lógica ADMIN-02:** la desactivación conserva historial y bloquea productos creados por empleados revocados.
- **Aislamiento ADMIN-03:** los endpoints `/admin/*` no alteran contratos de `/auth/*`, `/profiles/*` ni `/customer/*`.

## Datos y entidades

- **EN-01:** `Bodega`, ahora con `GET /admin/stores`; no se agregó columna `activo` porque el MVP no la necesita.
- **EN-02:** `Admin` y `Jefe`; `Jefe.estado` y `Admin.estado`/`fecha_creacion`/`ultimo_acceso` se agregaron de forma idempotente. `Jefe.estado` se respeta en login y bodega; `Admin.estado` se respeta en login y perfil del panel.
- **EN-03:** `ProductosBodega.creado_por` se usa al desactivar empleados desde admin, igual que en `/profiles/employees/{id}/revoke`.
- **EN-01/EN-02/EN-03 para `Cliente` y `Empleado`:** se listan con `UNION ALL`; el `id` expuesto es `rol:id` para evitar colisiones entre tablas.

## Criterios de aceptación

| Criterio | Estado en el prototipo | Validación pendiente |
|---|---|---|
| Menú admin propio con Panel, Cuentas, Bodegas y Perfil. | Implementado | Revisión visual en escritorio y móvil. |
| Paleta, tipografía y escala de `operations-web`. | Implementado | Revisión visual comparada. |
| Perfil muestra rol `Admin` y cierra sesión. | Implementado | Prueba en navegador. |
| Listado de cuentas de cuatro roles sin contraseñas. | Implementado | Prueba HTTP con token admin. |
| Admin no edita ni desactiva a otro admin. | Implementado | Prueba HTTP de `403` y revisión de botones deshabilitados. |
| Alta y edición con validación de correo, bodega y contraseña. | Implementado | Prueba HTTP de integración. |
| Desactivación lógica y bloqueo de productos de empleado. | Implementado | Prueba HTTP contra base desechable. |
| Cuenta demo sembrada y hasheada en arranque. | Implementado | Arranque limpio y verificación en base local. |
| `pytest` y `npm run build` pasan con los entornos definidos. | No verificado en este entorno | Ejecutar y registrar en `docs/06-quality/README.md`. |

## Escenarios de prueba

- `tests/test_admin_contract.py`: rutas, guard de otro admin, baja lógica, migraciones y token aislado.
- `tests/test_endpoint_usage.py`: cada ruta admin del backend es llamada por `apps/admin-web/src/lib/api.js`.
- Integración pendiente con base desechable: login admin, listado sin contraseñas, alta de jefe/empleado/cliente/admin, edición propia, `403` sobre otro admin, desactivación y bloqueo de productos.

## Dependencias y decisiones

- FastAPI + psycopg existentes; sin SQLAlchemy ni Alembic.
- Vite + React con los mismos tokens de diseño que `operations-web`.
- CORS incluye `5175` en local; producción debe definirse por variable de entorno.
- ADR-008 registra el cambio de alcance; ADR-001 se conserva para `operations-web`.

## Preguntas abiertas

- ¿Se publicará `admin-web` en un dominio propio distinto de `admin.bodesmart.com`? El README previo lo mencionaba como plan; no hay decisión confirmada de despliegue.
- ¿Se necesitará cambio de contraseña del propio admin? No se implementó en este corte porque no había endpoint seguro con verificación de contraseña actual.
- ¿Debe haber auditoría dedicada para altas/ediciones admin? ADR-008 no la define; hoy solo queda `ultimo_acceso`.
