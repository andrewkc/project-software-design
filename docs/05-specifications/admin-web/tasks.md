# ADMIN-01 — Tareas

## Backend

- [x] Agregar `require_admin()` en `security.py` sin alterar `identity_from_header()`.
- [x] Agregar CORS para `admin-web` en `config.py` y `.env.example`.
- [x] Crear `routers/admin.py` con login, perfil, usuarios, bodegas, alta, edición y desactivación.
- [x] Registrar el router en `main.py` sin tocar los otros routers.
- [x] Implementar `guard_admin_target()` para devolver `403` al intentar editar/desactivar otro admin.
- [x] Evitar la autodesactivación y el cambio de rol sobre una cuenta existente.
- [x] Ocultar contraseñas en todas las respuestas del listado y del detalle.
- [x] Agregar `Jefe.estado`, `Admin.estado`, `Admin.fecha_creacion`, `Admin.ultimo_acceso` y `ux_admin_correo_ci` en `ensure_schema()`.
- [x] Respetar `Jefe.estado` en `/auth/login` y `bodega_id_for()`.
- [x] Ampliar `email_exists()` a los cuatro roles.
- [x] Sembrar admin demo en `seed.sql` y hashearlo en el arranque con `ensure_demo_admin()`.
- [ ] Probar los endpoints contra una base desechable.

## Frontend

- [x] Crear `package.json`, Vite, Dockerfiles, `.dockerignore` e `index.html` de `admin-web`.
- [x] Crear cliente API con token `bodesmart-admin-token` y rutas `/admin/*`.
- [x] Replicar tokens de diseño: DM Sans/Manrope, `--font-scale: 1.4` global (`1.08` en acceso de escritorio), paleta y componentes base.
- [x] Crear layout con menú admin propio; la bottom nav se sustituyó por el menú desplegable de hamburguesa de ADR-009.
- [x] Crear login con credencial demo local.
- [x] Crear Panel con conteos por rol y bodegas.
- [x] Crear Cuentas con búsqueda, filtro, orden, drawer, confirmación y toast.
- [x] Crear Bodegas y Perfil con rol `Admin`.
- [x] Deshabilitar acciones sobre otros admins y sobre la propia cuenta.
- [ ] Ejecutar `npm run build` y revisar en navegador.

## Infraestructura y documentación

- [x] Agregar servicio `admin-web` a `docker-compose.yml`.
- [x] Actualizar README de backend, admin-web y `.env.example`.
- [x] Registrar ADR-008 y nota de superación parcial en ADR-001.
- [x] Crear especificación, plan y tareas de ADMIN-01.
- [x] Actualizar prueba estática de uso de endpoints con el cliente admin.
- [x] Agregar `tests/test_admin_contract.py`.
- [ ] Ejecutar `pytest`, builds y compose; registrar resultados en `docs/06-quality/README.md`.
