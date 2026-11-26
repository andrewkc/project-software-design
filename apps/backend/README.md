# BodeSmart API

Backend mínimo con FastAPI, organizado en módulos pequeños. La lógica y los endpoints son los mismos de la versión anterior.

| Archivo | Responsabilidad |
|---|---|
| `main.py` | App FastAPI, CORS, startup y endpoints utilitarios |
| `config.py` | DSN, secreto del token, duración y orígenes CORS |
| `security.py` | Hash bcrypt, tokens HMAC y dependencia de autenticación |
| `database.py` | Esquema de arranque, adaptadores de respuesta y consultas compartidas |
| `routers/auth.py` | Signup, login, perfil y cambio de contraseña |
| `routers/profiles.py` | Listado, alta y revocación de cuentas |
| `routers/products.py` | Listado, alta y edición de productos |
| `routers/customer.py` | Catálogo público, cuenta de comprador, reserva, pedido y pago de prueba |

## Arrancar

```powershell
cd C:\projects\project-software-design\apps\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Abre `http://localhost:8000/docs`.

## Imagen Docker

Desde esta carpeta:

```powershell
docker build -t bodesmart-backend .
docker run -d --name backend -p 8000:8000 `
  -e DATABASE_URL="postgresql://bodesmart:tu_password@host.docker.internal:5432/bodesmart" `
  bodesmart-backend
```

En Linux, para alcanzar un contenedor de base de datos en la misma red, reemplazá el host por el nombre del servicio, por ejemplo `database`. En Windows, `host.docker.internal` apunta a la máquina anfitriona. No pongas credenciales reales en el `Dockerfile`: pasalas con `-e` o con un archivo de entorno.

`.dockerignore` excluye `.venv`, `__pycache__` y cachés para no copiar el entorno de Windows al contexto de build.

## Variables de entorno

| Variable | Default | Uso |
|---|---|---|
| `DATABASE_URL` | DSN local del prototipo (`127.0.0.1:5432/bodesmart`) | Conexión a PostgreSQL; en contenedor debe apuntar al host de la BD |
| `BODESMART_SECRET` | valor de desarrollo | Firma del token |
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes permitidos, separados por coma |

El esquema base viene de `../database/database.sql`. Al arrancar, `database.py` agrega cuatro columnas que las reglas de roles necesitan y que aún no están en ese archivo:

- `Empleado.estado` para revocar acceso.
- `ProductosBodega.creado_por`, `.bloqueado` y `.bloqueado_por` para propiedad y bloqueo de filas.

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/auth/signup` | Crear bodega y jefe |
| `POST` | `/auth/login` | Login de jefe o empleado |
| `GET` | `/auth/me` | Perfil de la sesión actual |
| `POST` | `/auth/change-password` | Cambiar contraseña |
| `GET` | `/profiles` | Jefe y empleados de la bodega, solo jefe |
| `POST` | `/profiles/employees` | Crear empleado, solo jefe |
| `POST` | `/profiles/employees/{id}/revoke` | Revocar acceso y bloquear sus filas |
| `GET` | `/products` | Productos de la bodega del usuario |
| `POST` | `/products` | Crear producto en catálogo y bodega |
| `PATCH` | `/products/{id}` | Editar producto, bloquear, desactivar o reactivar |

## Tienda del comprador

`customer-web` utiliza las rutas `/customer/stores`, `/customer/offers`,
`/customer/auth/*` y `/customer/orders/*`. Los pedidos reservan stock diez
minutos; el importe y las líneas quedan congelados. La simulación local se
habilita con `ALLOW_SIMULATED_PAYMENT=true` (valor local por defecto).
`MERCADOPAGO_ACCESS_TOKEN` activa Checkout Pro de prueba; la comprobación de
aprobación se hace desde el servidor y verifica referencia, importe, moneda,
aplicación y cuenta del proveedor antes de descontar stock. La aplicación
cliente consulta el resultado después del pago. Si se configura
`MERCADOPAGO_WEBHOOK_SECRET`, la ruta `/customer/payments/webhook` acepta
notificaciones firmadas de prueba y consulta la orden al proveedor antes de
aplicar el cambio. En local la URL no es pública, por lo que la consulta desde
la aplicación sigue siendo necesaria.

El esquema existente se amplía al iniciar para aceptar datos anteriores. Para
una base nueva se usan `apps/database/database.sql` y `seed.sql`; el script
`seed_customer_demo.py` añade tres bodegas, ofertas y cuentas locales cuando
`BODESMART_DEMO_SEED=1`. La compra todavía usa el saldo agregado de
`ProductosBodega`; varios lotes por producto son una integración pendiente.

## Notas

- Todas las contraseñas se guardan con bcrypt: `/auth/signup` y `/profiles/employees` hashean antes de insertar. `seed.sql` no contiene credenciales. Al arrancar, `database.py` convierte cualquier contraseña en texto plano que haya quedado de una versión anterior. La verificación ya no acepta texto plano.
- `/auth/signup` reutiliza una bodega existente con el mismo nombre que no tenga jefe, para conservar el inventario sembrado.
- El token es un HMAC firmado con `BODESMART_SECRET`; no hay tabla de sesiones. La revocación se comprueba contra `Empleado.estado` en cada petición.
- `GET /products` hace JOIN entre `Producto` y `ProductosBodega`.
- `POST /products` escribe en ambas tablas y asigna `creado_por` al usuario autenticado.
- `PATCH /products/{id}` aplica `estado: "activo" | "inactivo"` a `ProductosBodega.estado`.
- El empleado solo edita filas activas, desbloqueadas y creadas por él. No puede bloquear ni desactivar.
