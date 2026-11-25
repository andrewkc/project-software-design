# BodegaSmart — prototipo frontend de operaciones

Prototipo adaptable a escritorio y móvil para la gestión interna de una bodega. Es la app que usan el **jefe** y el **empleado** en `app.bodesmart.com`. Ahora consume una API HTTP: el token se guarda en `localStorage` y los datos viven en PostgreSQL (`Bodega`, `Jefe`, `Empleado`, `Producto`, `ProductosBodega`). Los endpoints que llama todavía no están implementados en el backend.

## Ejecutar

Desde esta carpeta:

```bash
npm install
npm run dev
```

Para comprobar la compilación de producción:

```bash
npm run build
```

## Docker para EC2

El `Dockerfile` compila `dist` y lo sirve con nginx en el puerto 80. La URL de la API se hornea en el build, así que hay que pasarla como build arg:

```powershell
docker build -f .\apps\operations-web\Dockerfile -t theandrewkc/bodesmart-operations-web:latest `
  --build-arg VITE_API_BASE_URL="https://api.bodesmart.online" .\apps\operations-web
```

El contenedor se levanta en el EC2 con `-p 3002:80`, y el nginx del host hace proxy desde `app.bodesmart.online`.

## Docker local (sin nginx)

`Dockerfile` compila `dist` y lo sirve con nginx: es la imagen para el EC2. `Dockerfile.local` levanta el servidor de desarrollo de Vite directamente, para probar en tu máquina:

```powershell
cd C:\projects\project-software-design
docker build -f .\apps\operations-web\Dockerfile.local -t bodesmart-operations-web-local:latest .\apps\operations-web
docker run -d --name operations-web-local -p 5173:5173 bodesmart-operations-web-local:latest
```

Abrí `http://localhost:5173`. El backend debe estar corriendo y publicado en `127.0.0.1:8000`: la URL de la API se ejecuta en el navegador, por eso el default local es `http://localhost:8000`. Podés cambiarlo con `-e VITE_API_BASE_URL=...` al hacer `docker run`.

## API

La base URL se configura con `VITE_API_BASE_URL`. Por defecto usa `http://localhost:8000`.

Endpoints que consume el frontend:

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/auth/signup` | Crear jefe y bodega |
| `POST` | `/auth/login` | Iniciar sesión de jefe o empleado |
| `GET` | `/auth/me` | Restaurar la sesión al recargar |
| `POST` | `/auth/change-password` | Cambiar contraseña del empleado |
| `GET` | `/profiles` | Jefe y empleados, para etiquetas de autor y lista de cuentas |
| `POST` | `/profiles/employees` | Crear empleado |
| `POST` | `/profiles/employees/{id}/revoke` | Revocar acceso |
| `GET` | `/products` | Productos de la bodega del usuario |
| `POST` | `/products` | Registrar producto en el catálogo y en la bodega |
| `PATCH` | `/products/{id}` | Editar datos, stock, precio, vencimiento, bloqueo y estado |

El contrato de payloads y respuestas está documentado en `src/lib/api.js`.

## Cómo funciona

- **Acceso:** registro de jefe con nombres y apellidos separados, e inicio de sesión con correo y contraseña. El jefe crea cuentas de empleado con una contraseña inicial generada, puede revocar el acceso y permite al empleado cambiar su contraseña. Revocar conserva el historial y bloquea las filas del empleado.
- **Roles:** el jefe edita cualquier fila, incluidas las bloqueadas, y puede bloquear, desactivar y reactivar productos sin borrarlos. El empleado edita solo filas activas, desbloqueadas y creadas por él, incluido precio y stock, y accede únicamente a su bodega asignada.
- **Inventario:** alta de productos con icono emoji, búsqueda, ID por fila, autor de cada registro y edición en línea. Los cambios se envían al backend; el historial de movimientos queda fuera de este corte.
- **Alertas:** vencimientos calculados desde las fechas ingresadas. Las sugerencias de IA quedan fuera de este corte.
- **Registro de mercadería:** flujos demostrativos de foto, voz, escritura y código de barras. El navegador permite elegir o tomar una foto; voz, escaneo, análisis de imágenes y predicciones de IA no están conectados a servicios reales.
- **Hallazgos:** pantalla con control de memoria o papel, dificultad para registrar ventas, pérdidas por vencimiento y necesidad de identificar al responsable de cada movimiento.

Las decisiones de roles, propiedad y bloqueo son propuestas aplicadas al prototipo; la persistencia ahora apunta a la base PostgreSQL definida en `apps/database`. Los campos `creadoPor`, `bloqueado` y `bloqueadoPor` aún no existen en esa base y deben resolverse en el backend. Las entrevistas son exploratorias: el prototipo no demuestra reducción de pérdidas ni efectividad de la IA.

## Referencias

- [Visión del producto](../../docs/01-product/vision.md)
- [Alcance del MVP](../../docs/01-product/scope.md)
- [Requisitos funcionales RF-15 a RF-22](../../docs/03-requirements/functional-requirements.md)
- [Casos de uso CU-01 a CU-09](../../docs/02-business/use-cases/README.md)
- [Reglas de negocio RN-10 y RN-11](../../docs/02-business/business-rules.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [Preguntas abiertas](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)
