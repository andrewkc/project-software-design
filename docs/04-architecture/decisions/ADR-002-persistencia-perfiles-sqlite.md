# ADR-002: Persistencia de perfiles con SQLite en el prototipo

**Estado:** Propuesto / aplicado en el prototipo `operations-web`.

## Contexto

El prototipo guardaba los perfiles en `localStorage` (`bodega-jefe`, `bodega-employees`, `bodega-user`). El inicio de sesión solo buscaba el correo en esas claves y no existía una verificación de contraseña consistente para jefe y empleado. Se necesita una fuente única de perfiles que permita verificar credenciales al iniciar sesión y agregar registros al registrar una cuenta.

## Decisión

- Usar **SQLite en el navegador** mediante `sql.js` (WASM) para la tabla `profiles`.
- Columnas: `id`, `role`, `name`, `nombres`, `apellidos`, `email` (único), `password`, `store`, `activo`, `creado_en`, `revocado_en`.
- Al iniciar: `CREATE TABLE IF NOT EXISTS` y, si la tabla está vacía, migrar los perfiles existentes de `localStorage`.
- `login`: buscar por correo, validar que la cuenta esté activa y comparar contraseña. Las cuentas migradas sin contraseña conservan el comportamiento heredado.
- `signup` y alta de empleados: verificar correo duplicado e insertar el registro.
- La base de datos se exporta y se guarda como base64 en `bodega-profile-db`; las claves antiguas se mantienen como espejo para el resto del prototipo.
- Si `sql.js` no puede cargarse, se mantiene la ruta de `localStorage` como respaldo.

## Consecuencias

- Las credenciales siguen guardadas en texto plano: es un prototipo sin backend. En producción, SQLite debe estar en el servidor y las contraseñas deben hashearse.
- `sql.js` y su WASM se cargan desde CDN; el prototipo depende de red para usar SQLite.
- Queda abierta la definición del esquema definitivo y del mecanismo de autenticación real.
