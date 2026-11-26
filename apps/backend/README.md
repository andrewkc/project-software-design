# BodeSmart API

Backend mínimo con FastAPI, organizado en módulos pequeños. La lógica y los endpoints son los mismos de la versión anterior.

| Archivo | Responsabilidad |
|---|---|
| `main.py` | App FastAPI, CORS, startup y endpoints utilitarios |
| `config.py` | DSN, secreto del token, CORS, pagos de prueba y configuración de Gemini; carga `.env` |
| `security.py` | Hash bcrypt, tokens HMAC y dependencia de autenticación |
| `database.py` | Esquema de arranque, adaptadores de respuesta y consultas compartidas |
| `ai.py` | Adaptador de Gemini: prompt con campos permitidos, esquema y saneamiento |
| `routers/auth.py` | Signup, login, perfil y cambio de contraseña |
| `routers/admin.py` | `/admin/*`: login, perfil, cuentas y bodegas; aislado de jefe/empleado/cliente |
| `routers/profiles.py` | Listado, alta y revocación de cuentas |
| `routers/products.py` | Listado, alta y edición de productos; reutiliza/crea categoría al guardar |
| `routers/categories.py` | Listado y creación autenticados de categorías persistentes |
| `routers/registration.py` | `POST /products/extract`: borrador saneado desde foto, código o voz |
| `routers/recommendations.py` | Recomendaciones IA jefe-only, sin escritura en la base |
| `routers/sales.py` | Historial de compras pagadas y `POST /sales` transaccional |
| `routers/customer.py` | `/customer/*`: catálogo público, cuentas de cliente, reservas y pago de prueba |
| `sales_service.py` | Única regla de descuento de stock compartida por ventas y checkout |
| `seed_customer_demo.py` | Seed opcional y no destructivo de ofertas y comprador demo |

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
| `CORS_ORIGINS` | `localhost`/`127.0.0.1` en `5173`, `5174` y `5175` | Orígenes permitidos, separados por coma; en EC2 se reemplaza por los dominios correspondientes |
| `ALLOW_SIMULATED_PAYMENT` | `true` | Permite `POST /customer/orders/{id}/simulate-payment`; poner `false` fuera de la demo |
| `MERCADOPAGO_ACCESS_TOKEN` | vacía | Habilita el checkout de Mercado Pago **de prueba**; sin ella se usa `LOCAL_SIMULATION` |
| `MERCADOPAGO_WEBHOOK_SECRET` | vacía | Firma HMAC exigida por `POST /customer/payments/webhook` |
| `BODESMART_DEMO_SEED` | sin definir | Con `1`, permite ejecutar `seed_customer_demo.py` |
| `GEMINI_API_KEY` | vacía | Clave del proveedor; queda solo en el backend. Sin ella, el endpoint de IA responde `503` |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Modelo configurable; default provisional tras `503` por alta demanda de `3.5-flash-lite` |
| `GEMINI_ALLOWED_MODELS` | `gemini-3.1-flash-lite,gemini-3.5-flash-lite` | Opcional; ids que `GET /ai/models` publica y `POST /products/extract` acepta. Siempre incluye `GEMINI_MODEL` |
| `GEMINI_API_URL` | `https://generativelanguage.googleapis.com/v1beta/interactions` | Interactions API; `v1beta` es necesario para imagen/audio inline |
| `OPEN_FOOD_FACTS_API_URL` | `https://world.openfoodfacts.org/api/v2/product` | Consulta pública de códigos para REG-IA `Código`, sin key |
| `OPEN_FOOD_FACTS_USER_AGENT` | `BodeSmart/0.1 (local-prototype)` | Identificación ante Open Food Facts; configurar contacto en producción |

El esquema base viene de `../database/database.sql`. Al arrancar, `database.py` agrega de forma idempotente las columnas que las reglas de roles y el contrato de compras necesitan:

- `Empleado.estado` y `Jefe.estado` para revocar acceso; un jefe inactivo ya no inicia sesión ni resuelve su bodega.
- `Admin.estado`, `Admin.fecha_creacion`, `Admin.ultimo_acceso` y el índice `ux_admin_correo_ci` para el panel administrativo. `ensure_demo_admin()` inserta la cuenta demo si faltaba en una base creada antes del seed.
- `ProductosBodega.creado_por`, `.bloqueado` y `.bloqueado_por` para propiedad y bloqueo de filas.
- `Oferta.id_bodega` y `.precio_original`; `Compra.reserva_hasta`, `.idempotency_key`, `.request_hash` y `.fecha_pago`; `DetalleCompra.id_oferta`; `Pago.clave_proveedor`, `.checkout_url`, `.proveedor_app_id` y `.proveedor_user_id`.
- Crea `ReservaCompra` y el índice parcial `ix_reserva_activa` si no existen.

También crea `Categoria(nombre VARCHAR(100) PRIMARY KEY, fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP)` si falta, migra categorías existentes desde `Producto` con `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))` y siembra las nueve categorías base. `normalize_category`, `list_categories` y `ensure_category` reutilizan nombres sin distinguir mayúsculas/minúsculas, crean la que falte y truncan a 100 caracteres. `Producto.categoria` sigue `VARCHAR(100)` con el nombre de una sola categoría: relación lógica, no FK física.

`sales_service.ensure_demo_sales()` siembra tres compras pagadas sintéticas de `cliente.demo@bodesmart.local` con claves de idempotencia fijas. Cada compra descuenta stock dentro de la misma transacción; si la clave ya existe, no vuelve a descontar. No hay datos reales de clientes ni cobro: `Pago.metodo_pago = 'LOCAL_SIMULATION'` es solo la traza del prototipo. `ensure_storefront_offers()` deriva de `ProductosBodega` el catálogo local de Bodega San Martín: publica productos activos, no bloqueados, con vencimiento futuro y stock, a su precio real; un subconjunto fijo recibe 20% de descuento y las ofertas ya existentes nunca se sobrescriben. `seed_customer_demo.py` agrega tiendas, ofertas y un comprador aparte sin modificar jefes, empleados, contraseñas ni precios existentes.

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Estado del servicio |
| `POST` | `/auth/signup` | Crear bodega y jefe |
| `POST` | `/auth/login` | Login de jefe o empleado |
| `GET` | `/auth/me` | Perfil de la sesión actual |
| `POST` | `/auth/change-password` | Cambiar contraseña |
| `POST` | `/admin/auth/login` | Login de administrador de plataforma |
| `GET` | `/admin/me` | Perfil del administrador |
| `GET` | `/admin/users` | Todas las cuentas, sin contraseñas, solo admin |
| `POST` | `/admin/users` | Crear cuenta de cualquier rol, solo admin |
| `GET` | `/admin/stores` | Bodegas disponibles, solo admin |
| `PATCH` | `/admin/users/{id}` | Editar cuenta; otro admin no es editable |
| `DELETE` | `/admin/users/{id}` | Desactivar cuenta; otro admin no es desactivable |
| `GET` | `/profiles` | Jefe y empleados de la bodega, solo jefe |
| `POST` | `/profiles/employees` | Crear empleado, solo jefe |
| `POST` | `/profiles/employees/{id}/revoke` | Revocar acceso y bloquear sus filas |
| `GET` | `/products` | Productos de la bodega del usuario |
| `POST` | `/products` | Crear producto en catálogo y bodega |
| `PATCH` | `/products/{id}` | Editar producto, bloquear, desactivar o reactivar; reutiliza/crea categoría |
| `GET` | `/categories` | Categorías persistentes disponibles, autenticado |
| `POST` | `/categories` | Crear una categoría o reutilizarla si ya existe, autenticado |
| `POST` | `/recommendations/generate` | Sugerencias IA de descuento, aumento y reposición, solo jefe |
| `GET` | `/ai/models` | Modelos Gemini autorizados para el selector de `Foto`/`Voz`; jefe y empleado |
| `POST` | `/products/extract` | Borrador IA desde foto, imagen de código o voz; jefe y empleado |
| `GET` | `/sales` | Historial de compras pagadas de la bodega, jefe y empleado |
| `POST` | `/sales` | Alta transaccional de una compra pagada de un `Cliente`, jefe y empleado |
| `GET` | `/customer/stores` | Bodegas disponibles para el catálogo público |
| `GET` | `/customer/offers` | Ofertas vigentes con disponible = stock − reservas activas; `?store_id=` opcional |
| `POST` | `/customer/auth/register` | Alta de comprador y token `cliente` |
| `POST` | `/customer/auth/login` | Login de comprador |
| `GET` | `/customer/auth/me` | Perfil del comprador |
| `GET` | `/customer/payment-methods` | Etiquetas y disponibilidad de métodos; nunca expone credenciales |
| `GET` | `/customer/orders` | Todos los pedidos del comprador, con su estado y `payment_mode` |
| `POST` | `/customer/orders` | Reserva por diez minutos, sin descuento de stock; UUID idempotente y método persistido en `Pago` |
| `GET` | `/customer/orders/{id}` | Detalle de un pedido propio |
| `POST` | `/customer/orders/{id}/simulate-payment` | Aprobación local de prueba, si `ALLOW_SIMULATED_PAYMENT` está activo |
| `POST` | `/customer/orders/{id}/checkout` | Abre orden de Mercado Pago de prueba y guarda la URL verificada |
| `POST` | `/customer/orders/{id}/verify-payment` | Consulta server-side y aprueba, rechaza o marca `pago_en_revision` |
| `POST` | `/customer/payments/webhook` | Notificación firmada HMAC; no la llama el navegador |

## Notas

- Todas las contraseñas se guardan con bcrypt: `/auth/signup`, `/profiles/employees`, `/admin/users` y `/admin/auth/login` hashean o verifican antes de insertar/validar. La única excepción visible en `seed.sql` es la cuenta demo `admin@bodesmart.local` / `Admin123456`, que `ensure_schema()` rehashea en el arranque; no es una credencial de producción. La verificación ya no acepta texto plano.
- `/auth/signup` reutiliza una bodega existente con el mismo nombre que no tenga jefe, para conservar el inventario sembrado.
- El token es un HMAC firmado con `BODESMART_SECRET`; no hay tabla de sesiones. La revocación se comprueba contra `Empleado.estado` y `Jefe.estado` en cada petición correspondiente.
- Las rutas `/admin/*` usan el mismo token Bearer con `rol = 'admin'` y no cambian los contratos de jefe, empleado ni cliente. `guard_admin_target()` devuelve `403` si un administrador intenta editar/desactivar a otro administrador; la autodesactivación responde `400`. `DELETE /admin/users/{id}` nunca borra filas: marca `estado = 'inactivo'` y, si es empleado, bloquea sus productos como en la revocación del jefe. Ver [ADR-008](../../docs/04-architecture/decisions/ADR-008-admin-web-alcance-cuentas.md).
- `GET /products` hace JOIN entre `Producto` y `ProductosBodega`.
- `POST /products` escribe en ambas tablas y asigna `creado_por` al usuario autenticado.
- `POST /products/extract` no escribe en la base: valida multimedia (imagen o audio ≤ 8 MB, audio ≤ 60 s) y devuelve un borrador saneado. `photo`/`voice` llaman a Gemini con `store: false`; `barcode` exige imagen y consulta Open Food Facts con los dígitos ya procesados, sin `google_search`. Si no hay coincidencia, responde `200` con mensaje de registro manual.
- `voice` transcribe los ocho campos dictados —`nombre`, `icono`, `categoria`, `cantidad`, `unidad`, `precio_venta`, `fecha_vencimiento` y `codigo_barras`— solo cuando fueron dichos explícitamente; la fecha se expresa ISO `AAAA-MM-DD` y la IA no estima vida útil. El prompt recibe `list_categories(conn)`; `CATEGORIAS` conserva las mismas nueve categorías base del seed/UI como fallback. `photo` no propone precio, vencimiento ni código; `barcode` no propone cantidad, precio ni vencimiento.
- `GET /ai/models` devuelve `{default, modelos: [{id, label, activo}], nota}`; la clave y la URL del proveedor no se exponen. `POST /products/extract` acepta `modelo` solo en `photo`/`voice`: vacío usa `GEMINI_MODEL`, un id de la allowlist se usa y se informa en `proveedor`/`modelo`, y cualquier otro id responde `400`. `barcode` ignora el campo porque usa Open Food Facts. El selector no soluciona por sí solo un `503` de alta demanda.
- `POST /categories` guarda solo el catálogo de categorías. La creación de categoría desde el formulario no crea producto ni movimiento; el producto se guarda con `POST /products`.
- `PATCH /products/{id}` aplica `estado: "activo" | "inactivo"` a `ProductosBodega.estado`.
- El empleado solo edita filas activas, desbloqueadas y creadas por él. No puede bloquear ni desactivar.
- `POST /recommendations/generate` filtra por la bodega del jefe y envía a Gemini solo `nombre`, `categoria`, `stock`, `precio_venta`, `fecha_vencimiento` y `estado`. Usa `store: false`, sanea la respuesta y no escribe en PostgreSQL. La IA no aprueba cambios, genera compras ni modifica inventario; el jefe confirma manualmente con `PATCH /products/{id}` si decide revisar un precio.
- `GET /sales` solo devuelve `Compra.estado = 'pagado'` de la bodega del token; nunca muestra reservas, pedidos pendientes, expirados, rechazados ni pagos en revisión porque esos estados no descontaron stock.
- `POST /sales` valida `Cliente` activo, cantidades positivas, producto activo, fecha de vencimiento futura (o nula) y precio positivo; bloquea las filas de `ProductosBodega` con `FOR UPDATE`, descuenta con `UPDATE ... WHERE stock >= cantidad RETURNING stock` y guarda `Compra`, `DetalleCompra`, `ReservaCompra` en estado `consumida` y `Pago` en una sola transacción. La idempotencia por UUID evita duplicar la compra y el descuento. `id_oferta` es opcional; si se envía debe estar vigente para ese producto y bodega, y congela `precio_oferta`.
- `/customer/orders` no descuenta stock: crea `ReservaCompra` activa y guarda `request_hash` con UUID idempotente. Si la UI envía `metodo_pago`, se persiste en `Pago` y se devuelve como `payment_mode`; los clientes antiguos que omiten el campo conservan el comportamiento previo y el proveedor se resuelve al iniciar `checkout`. `GET /customer/payment-methods` solo publica etiquetas y disponibilidad: Mercado Pago aparece inactivo sin `MERCADOPAGO_ACCESS_TOKEN` y la clave nunca sale del backend. El descuento ocurre una sola vez en `sales_service.approve_reserved_order()`, compartido con `POST /sales` mediante `decrement_stock_once()`. Un pago acreditado después del vencimiento queda `pago_en_revision` y no toma existencias.
- `/customer/*` exige token `rol = 'cliente'`; un token de jefe/empleado recibe `403`. Cada pedido se filtra por `id_cliente`, así que otro comprador recibe `404`. El webhook exige `X-Request-Id`, `X-Signature` con `ts`/`v1` y `live_mode: false`.
- Pruebas sin base: `python -m pytest tests/test_sales.py tests/test_endpoint_usage.py tests/test_customer_contract.py -v` desde la raíz. Las de integración del checkout necesitan una base desechable y se omiten si no se define explícitamente: `DATABASE_URL=BODESMART_TEST_DATABASE_URL=... python -m pytest tests/test_customer_flow.py -v`.
- Ver [ADR-007](../../docs/04-architecture/decisions/ADR-007-cliente-web-pago-prueba.md).
- Ver [ADR-004](../../docs/04-architecture/decisions/ADR-004-gemini-recomendaciones-ia.md), [REC-IA](../../docs/05-specifications/recomendaciones-ia/spec.md), [ADR-005](../../docs/04-architecture/decisions/ADR-005-registro-asistido-por-ia.md) y [REG-IA](../../docs/05-specifications/registro-asistido-ia/spec.md). Las reglas vigentes están en RN-12/RN-13/RN-14/RN-17 y RF-25…RF-30/RF-34; la precisión del dictado, los dos modelos autorizados y la ejecución de pruebas están pendientes de validación.
