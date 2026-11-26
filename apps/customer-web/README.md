# BodeSmart · customer-web

Tienda de clientes del MVP ampliado (ADR-007). Usa los mismos tokens visuales, tipografía, menú y tarjeta de perfil que `operations-web`; el perfil muestra el rol `Cliente`. Las secciones son `Inicio`, `Bodegas`, `Mi cesta`, `Mis pedidos` y `Perfil`. La pantalla de acceso conserva la escala tipográfica anterior (`1.08` en escritorio y `1.4` en móvil); el titular «Compra mejor. Aprovecha más.» se achicó y el título de «Ingresar como cliente» / «Crear cuenta de cliente» se agrandó (`34px × escala` en escritorio, `31px × escala` en móvil y ventanas bajas), manteniendo márgenes compactos para no requerir scroll. El logo oficial se muestra directo sobre el panel verde, sin recuadro blanco ni crema.

## Arrancar

```powershell
cd C:\projects\project-software-design\apps\customer-web
npm install
npm run dev
```

Vite sirve en `http://127.0.0.1:5174`. La API se toma de `VITE_API_BASE_URL` (por defecto `http://127.0.0.1:8000`), así que el backend debe tener `5174` en `CORS_ORIGINS`. El token se guarda en `bodesmart_customer_token`.

Los logos oficiales se copian automáticamente desde `apps/operations-web/src/assets` a `public/assets` antes de `dev` y `build` (`npm run copy-logos`). La pantalla de acceso usa esos archivos y mantiene un escalado tipográfico propio y compacto para que login y registro quepan sin desplazamiento en portátil.

Si la base aún no tiene ofertas, ejecutar desde la raíz:

```powershell
$env:BODESMART_DEMO_SEED = "1"
python apps/backend/seed_customer_demo.py
```

Eso agrega tiendas, ofertas vigentes y un comprador demo sin sobrescribir jefes, empleados ni precios. Las credenciales quedan en `.demo-credentials.json` (ignorado por Git). También sirve la cuenta `cliente.demo@bodesmart.local` / `DemoCliente2026!` creada por `ensure_demo_sales()`.

## Flujo de compra

1. `/customer/offers` publica ofertas vigentes; `available` ya descuenta las reservas activas.
2. La cesta solo admite productos de una bodega. `POST /customer/orders` crea una reserva de diez minutos con UUID idempotente; **no descuenta stock**.
3. `Simular pago` usa `LOCAL_SIMULATION`. Si hay `MERCADOPAGO_ACCESS_TOKEN`, el botón abre el checkout de Mercado Pago de prueba y `verify-payment` consulta al proveedor desde el backend.
4. Solo la aprobación verificada descuenta stock. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` se muestran en `Mis pedidos` y nunca descuentan inventario.

La exploración con datos de ejemplo aparece si el backend no responde y también desde «Explorar la tienda con datos de demostración». Es solo local: no persiste pedidos, no modifica inventario y no sustituye al checkout cuando el backend está disponible. Es una demo académica: no hay cobros reales.

## Docker

Desde la raíz del repositorio, el compose ya incluye el servicio `customer-web` junto a `database`, `backend` y `operations-web`:

```powershell
docker compose up -d --build customer-web
```

Publica `127.0.0.1:5174:80` por defecto. El `Dockerfile` compila `dist` y lo sirve con nginx; la URL de la API se hornea en el build, por eso se pasa como build arg (`CUSTOMER_VITE_API_BASE_URL` en el compose). Para levantar solo el servidor de desarrollo de Vite sin nginx:

```powershell
$env:CUSTOMER_DOCKERFILE = "Dockerfile.local"
$env:CUSTOMER_CONTAINER_PORT = "5174"
docker compose up -d --build customer-web
```

La URL de la API se ejecuta en el navegador, así que el default local es `http://127.0.0.1:8000`. El backend debe incluir `http://127.0.0.1:5174` en `CORS_ORIGINS` (el compose lo agrega cuando esa variable no está definida). Si definís `CORS_ORIGINS` en `.env`, includí todos los orígenes que uses. Para un despliegue con HTTPS, configurá `CUSTOMER_VITE_API_BASE_URL` con la URL pública de la API.

## Marca y perfil

Los logos oficiales se copian desde `apps/operations-web/src/assets` a `customer-web/public/assets` con `npm run copy-logos`; npm lo ejecuta automáticamente antes de `dev` y `build`. `Brand` usa el logo completo en el panel de acceso y el compacto en la barra lateral y en móvil. Si los archivos aún no están, cae al wordmark verde ya existente, así que la interfaz no queda rota.

La sección `Perfil` reutiliza la misma tarjeta de la esquina inferior izquierda (avatar con inicial, nombre corto, rol `Cliente` y los tres puntos). Los datos de la cuenta, el conteo de pedidos pagados y «Cerrar sesión» quedan en tarjetas separadas debajo.
