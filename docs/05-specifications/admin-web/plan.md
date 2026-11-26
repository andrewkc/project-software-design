# ADMIN-01 — Plan técnico

## Decisión previa

Implementar el corte mínimo acordado en ADR-008 sin tocar los contratos existentes de jefe, empleado ni cliente. La fuente de verdad es `ADMIN-01/spec.md`; este plan solo describe cómo se llevó a código.

## Arquitectura

1. **Backend:** router nuevo `routers/admin.py` con prefijo literal `/admin` en cada decorator. Usa `psycopg`, `dict_row`, bcrypt y el mismo HMAC Bearer del proyecto. No agrega dependencias nuevas.
2. **Seguridad:** `security.require_admin()` verifica `rol == 'admin'`; `guard_admin_target()` impide modificar a otro admin. No se copia cookies/CSRF ni `/auth/demo-admin`.
3. **Esquema:** `database.ensure_schema()` agrega DDL idempotente. `seed.sql` siembra la cuenta demo. `ensure_demo_admin()` rellena bases preexistentes y el bucle de hash convierte la contraseña de texto en bcrypt.
4. **Frontend:** app Vite/React independiente en `apps/admin-web`, con cliente API propio y token `bodesmart-admin-token`. Reutiliza tokens visuales y patrones de `operations-web` sin importar su código ni su localStorage.
5. **Compose:** servicio `admin-web`, variables `ADMIN_DOCKERFILE`, `ADMIN_PORT` y `ADMIN_CONTAINER_PORT`; CORS incluye `5175` en local.

## Contrato

| Método | Ruta | Regla |
|---|---|---|
| POST | `/admin/auth/login` | `correo`, `password`; Estado `activo`; devuelve token y perfil. |
| GET | `/admin/me` | Exige `rol = admin` y cuenta activa. |
| GET | `/admin/users` | `UNION ALL` de Admin, Jefe, Empleado y Cliente; sin password. |
| POST | `/admin/users` | Crea cualquiera de los cuatro roles; bcrypt; bodega obligatoria para jefe/empleado. |
| GET | `/admin/stores` | Bodegas ordenadas por nombre. |
| PATCH | `/admin/users/{uid}` | Campos permitidos; sin cambio de rol; guard de otro admin. |
| DELETE | `/admin/users/{uid}` | Desactivación lógica; guard de otro admin y de la propia cuenta. |

El `uid` expuesto es `rol:id` (`admin:1`, `jefe:12`, etc.) para conservar unicidad entre tablas con `SERIAL` independiente.

## Compatibilidad

- `/auth/login` solo consulta `Jefe` y `Empleado`; no se mezcla con `Admin`.
- `/auth/me` y `fetch_profile()` siguen sin conocer el rol `admin`; admin-web usa `/admin/me`.
- `email_exists()` ahora revisa cuatro tablas, evitando correos repetidos entre roles; `auth/signup` y `profiles/employees` conservan su respuesta.
- `Jefe.estado` se agrega con default `activo`, por lo que las filas existentes siguen funcionando.
- CORS agrega `5175` sin quitar `5173` ni `5174`.

## Fuera del plan

- Auditoría de acciones admin.
- Cambio de contraseña del admin con verificación de contraseña actual.
- Bodegas con estado `activo/inactivo`.
- Cotas de memoria, rendimiento o métricas de negocio no pedidas.
- Reintentos automáticos de IA, sugerencias de compra ni escritura de inventario desde IA.

## Validación prevista

- Estática: `tests/test_admin_contract.py` y `tests/test_endpoint_usage.py` con `apps\backend\.venv`.
- Build: `npm run build` en `apps/admin-web` y regresión en `apps/operations-web`.
- HTTP con base desechable: login, alta, edición, `403` sobre otro admin, desactivación, login de jefe desactivado.
- Compose: `docker compose up -d --build backend operations-web admin-web` sin `down -v`.
- Registro de resultados reales en `docs/06-quality/README.md`.
