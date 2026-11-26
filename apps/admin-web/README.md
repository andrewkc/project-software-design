# admin-web

## Estado

Implementado como primer corte local. No está desplegado ni validado en producción; forma parte de un prototipo académico con entrevistas exploratorias.

La app usa Vite + React, el mismo proveedor de estilos de `operations-web` (DM Sans/Manrope, `--font-scale: 1.4`, paleta `#397a55`/`#f7f8f3`/`#252c26`) y el contrato Bearer del backend actual. No guarda claves de IA: el token de Gemini vive solo en el backend y el panel no consulta costos, ventas ni márgenes.

El favicon se sirve desde `public/favicon.png` con un `<link rel="icon">` en `index.html`, igual que en `operations-web` y `customer-web`. En móvil (≤720 px) no hay barra inferior con varias secciones: un botón de hamburguesa abierto desde la esquina inferior despliega `Panel`, `Cuentas`, `Bodegas` y `Mi cuenta`. La escala sube a `1.55` y el texto secundario tiene un piso de `9px × escala`; la pantalla de acceso mantiene `1.4` para caber sin desplazamiento. Ver [ADR-009](../../docs/04-architecture/decisions/ADR-009-shell-movil-favicon.md).

## Secciones

- **Panel:** conteos de cuentas por rol y bodegas registradas.
- **Cuentas:** tabla con búsqueda, filtro por rol, orden, drawer de alta/edición y desactivación con confirmación.
- **Bodegas:** listado de bodegas y cuentas asignadas.
- **Perfil:** se abre desde la tarjeta de cuenta de la esquina inferior izquierda; en móvil, desde «Mi cuenta» en el panel desplegable. No hay entrada duplicada con la etiqueta `Perfil`; cuenta `Admin`, con cierre de sesión y regla de autoprotección.

Un administrador puede gestionar jefes, empleados, clientes y su propia cuenta. No puede editar ni desactivar cuentas de otros administradores, ni desactivar la suya. La baja siempre es lógica para conservar historial.

## Arranque local

Requiere el backend en `http://localhost:8000` y el CORS habilitado para `http://localhost:5175`.

```powershell
cd C:\projects\project-software-design\apps\admin-web
npm install
npm run dev
```

La app queda en `http://localhost:5175`. Para compilar:

```powershell
npm run build
```

El resultado queda en `dist/`. La URL de la API se define con `VITE_API_BASE_URL` (por defecto `http://localhost:8000`). El token se guarda en `localStorage` bajo `bodesmart-admin-token`, separado del token de `operations-web`. Este corte aún no versiona `package-lock.json`, así que los Dockerfiles usan `npm install` en vez de `npm ci`; `Dockerfile.local` respeta el build arg `VITE_API_BASE_URL`.

Los logos oficiales se copian automáticamente desde `apps/operations-web/src/assets` a `public/assets` antes de `dev` y `build` (`npm run copy-logos`). `Brand.jsx` los sirve desde `/assets/...`: logo completo directo sobre el verde en el panel de acceso y logo compacto en el sidebar y en móvil.

## Cuenta demo local

`apps/database/seed.sql` siembra:

- correo: `admin@bodesmart.local`
- contraseña: `Admin123456`

Es una credencial de prototipo, hasheada con bcrypt por `ensure_schema()` en el primer arranque del backend. No debe usarse fuera de la demo local. La interfaz de acceso ya no la muestra; se documenta aquí solo para la prueba local.

## Endpoints usados

- `POST /admin/auth/login`
- `GET /admin/me`
- `GET /admin/users`
- `POST /admin/users`
- `GET /admin/stores`
- `PATCH /admin/users/{id}`
- `DELETE /admin/users/{id}`

## Docker Compose

El servicio `admin-web` expone `127.0.0.1:${ADMIN_PORT:-5175}` y usa `ADMIN_DOCKERFILE` (`Dockerfile` con nginx o `Dockerfile.local` con Vite). Tras cambiar código, hacer rebuild explícito:

```powershell
docker compose up -d --build backend operations-web admin-web
```

No usar `down -v` salvo reset consciente: el volumen `db-data` contiene la base local.

## Referencias

- [CU-01 Administrar cuentas y accesos](../../docs/02-business/use-cases/cases/CU-01.md)
- [RF-01 y RF-19](../../docs/03-requirements/functional-requirements.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-008 Alcance del panel administrativo](../../docs/04-architecture/decisions/ADR-008-admin-web-alcance-cuentas.md)
- [Preguntas abiertas 19 a 21](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)
