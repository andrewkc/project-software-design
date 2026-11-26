# BodegaSmart — prototipo frontend de operaciones

Prototipo adaptable a escritorio y móvil para la gestión interna de una bodega. Es la app que usan el **jefe** y el **empleado** en `app.bodesmart.online`. Consume una API HTTP: el token se guarda en `localStorage` y los datos viven en PostgreSQL (`Bodega`, `Jefe`, `Empleado`, `Producto`, `ProductosBodega`).

El favicon se sirve desde `public/favicon.png` con un `<link rel="icon">` en `index.html`, igual que en `customer-web` y `admin-web`. En móvil (≤720 px) la barra inferior de cinco secciones se reemplazó por un botón de hamburguesa en la esquina inferior derecha: el panel desplegable respeta el rol (jefe ve `Recomendaciones` y `Empleados`; empleado ve `Perfil`) e incluye siempre `Inicio`, `Inventario`, `Registrar`, `Vencimientos` y `Ventas`. La escala general sube a `1.55` con piso de `9px × escala` para tablas, badges y texto secundario. Ver [ADR-009](../../docs/04-architecture/decisions/ADR-009-shell-movil-favicon.md).

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
| `GET` | `/ai/models` | Modelos Gemini autorizados para el selector de `Foto`/`Voz` |
| `POST` | `/products/extract` | Obtener un borrador IA desde foto, imagen de código o voz |
| `PATCH` | `/products/{id}` | Editar datos, stock, precio, vencimiento, bloqueo y estado |
| `POST` | `/recommendations/generate` | Generar sugerencias IA solo para el jefe |
| `GET` | `/sales` | Historial de compras pagadas de la bodega, visible para jefe y empleado |

El contrato de payloads y respuestas está documentado en `src/lib/api.js`.

## Cómo funciona

- **Acceso:** registro de jefe con nombres y apellidos separados, e inicio de sesión con correo y contraseña. El jefe crea cuentas de empleado con una contraseña inicial generada, puede revocar el acceso y permite al empleado cambiar su contraseña. Revocar conserva el historial y bloquea las filas del empleado.
- **Roles:** el jefe edita cualquier fila, incluidas las bloqueadas, y puede bloquear, desactivar y reactivar productos sin borrarlos. El empleado edita solo filas activas, desbloqueadas y creadas por él, incluido precio y stock, y accede únicamente a su bodega asignada.
- **Inventario:** alta de productos con icono emoji, búsqueda, ID por fila, autor de cada registro y edición en línea. Los cambios se envían al backend; el historial de movimientos queda fuera de este corte.
- **Alertas:** vencimientos calculados desde las fechas ingresadas.
- **Ventas:** sección visible para jefe y empleado con el historial de compras pagadas de los clientes de la bodega. Solo muestra `Compra.estado = 'pagado'`: cada registro descontó el stock en la misma transacción en que se guardó, con precios y cantidades congelados. Los pedidos pendientes, expirados, rechazados o en revisión no aparecen porque no son ventas. Las compras de `customer-web` llegan aquí por el mismo contrato; la vista recarga ventas e inventario al enfocar la pestaña, cada 15 s y con el botón «Actualizar», para no depender de la instantánea del inicio de sesión. El backend todavía siembra tres compras sintéticas históricas para la demo local; son datos de ejemplo, no compras de clientes reales. El inicio reutiliza ese mismo historial en la gráfica «Ventas acumuladas», sin series ni totales inventados.
- **Recomendaciones IA:** sección jefe-only con sugerencias de descuento, aumento y reposición generadas por Gemini desde el backend. La clave nunca llega al navegador. Al revisar un precio se abre el formulario; nada se guarda hasta que el jefe confirma. La reposición es solo referencia: no crea compras ni cambia stock. Sin clave o sin proveedor se muestra un error y el inventario sigue disponible. Es un prototipo pendiente de validación con clave real.
- **Registro asistido:** `Foto` y `Voz` envían multimedia real al backend, que llama a Gemini y devuelve un borrador saneado. `Código` valida la imagen y consulta Open Food Facts con los dígitos ya procesados; si no hay coincidencia, muestra un mensaje para registrar manualmente. La cantidad, el precio y el vencimiento los ingresa el usuario. Todos los campos son editables y nada se guarda hasta que confirma el formulario. Sin clave de Gemini, `Foto`/`Voz` muestran un error y el registro manual sigue disponible. En `Foto`/`Voz` hay un selector de modelo: el backend publica solo los ids autorizados con `GET /ai/models`, rechaza cualquier otro y mantiene la clave fuera del navegador. Si un modelo devuelve `503` por alta demanda, se puede esperar, reintentar o probar otro autorizado; no se aplica nada automáticamente. Es un prototipo pendiente de validación real.
- **Hallazgos:** pantalla con control de memoria o papel, dificultad para registrar ventas, pérdidas por vencimiento y necesidad de identificar al responsable de cada movimiento.

Las decisiones de roles, propiedad y bloqueo son propuestas aplicadas al prototipo; la persistencia ahora apunta a la base PostgreSQL definida en `apps/database`. Los campos `creadoPor`, `bloqueado` y `bloqueadoPor` se agregan de forma idempotente desde `ensure_schema()`. Las entrevistas son exploratorias: el prototipo no demuestra reducción de pérdidas ni efectividad de la IA.

## Referencias

- [Visión del producto](../../docs/01-product/vision.md)
- [Alcance del MVP](../../docs/01-product/scope.md)
- [Requisitos funcionales RF-15 a RF-22](../../docs/03-requirements/functional-requirements.md)
- [Casos de uso CU-01 a CU-09](../../docs/02-business/use-cases/README.md)
- [Reglas de negocio RN-10 y RN-11](../../docs/02-business/business-rules.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [ADR-004 Gemini para recomendaciones IA](../../docs/04-architecture/decisions/ADR-004-gemini-recomendaciones-ia.md)
- [ADR-006 Historial de ventas y compra atómica](../../docs/04-architecture/decisions/ADR-006-ventas-historial-compra-atomica.md)
- [Especificación REC-IA](../../docs/05-specifications/recomendaciones-ia/spec.md)
- [Preguntas abiertas](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)
