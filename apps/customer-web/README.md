# BodeSmart · customer-web

Tienda de clientes del MVP ampliado (ADR-007). Usa los mismos tokens visuales, tipografía, menú y tarjeta de perfil que `operations-web`; el perfil muestra el rol `Cliente`. El menú tiene cuatro secciones (`Inicio`, `Bodegas`, `Mi cesta`, `Mis pedidos`): `Perfil` no se repite como entrada, se abre desde la tarjeta de cuenta; en móvil el panel desplegable incluye «Mi cuenta». La pantalla de acceso usa `1.2` en escritorio y `1.4` en móvil; el titular «Compra mejor. Aprovecha más.» se ajustó a `clamp(38px, 4.6vw, 56px)` (`clamp(34px, 4vw, 48px)` en ventanas bajas) y el párrafo de apoyo a `17px × escala`, mientras que el título de «Ingresar como cliente» / «Crear cuenta de cliente» se mantiene en `34px × escala` en escritorio y `31px × escala` en móvil y ventanas bajas, con márgenes compactos para no requerir scroll. El logo oficial se muestra directo sobre el panel verde, sin recuadro blanco ni crema; en la vista interna el botón del sidebar no dibuja borde ni fondo.

El favicon se sirve desde `public/favicon.png` con un `<link rel="icon">` en `index.html`, igual que en `operations-web` y `admin-web`. En móvil (≤720 px) la barra inferior de cuatro secciones se reemplazó por un botón de hamburguesa en la esquina inferior que despliega hacia arriba las cuatro secciones y «Mi cuenta»; la escala general sube a `1.55` con un piso de `9px × escala` para texto secundario. Ver [ADR-009](../../docs/04-architecture/decisions/ADR-009-shell-movil-favicon.md).

## Arrancar

```powershell
cd C:\projects\project-software-design\apps\customer-web
npm install
npm run dev
```

Vite sirve en `http://127.0.0.1:5174`. La API se toma de `VITE_API_BASE_URL` (por defecto `http://127.0.0.1:8000`), así que el backend debe tener `5174` en `CORS_ORIGINS`. El token se guarda en `bodesmart_customer_token`.

Los logos oficiales se copian automáticamente desde `apps/operations-web/src/assets` a `public/assets` antes de `dev` y `build` (`npm run copy-logos`). La pantalla de acceso usa esos archivos y mantiene un escalado tipográfico propio y compacto para que login y registro quepan sin desplazamiento en portátil.

`ensure_schema()` publica automáticamente el catálogo de Bodega San Martín: lee `ProductosBodega`, toma solo productos activos, no bloqueados, con vencimiento futuro y stock, y crea una `Oferta` por producto con precio real; solo un subconjunto fijo recibe 20% de descuento, el resto se muestra a precio normal. No sobrescribe ofertas existentes, así que reiniciar el backend no cambia precios ni stock. El listado de bodegas muestra cuántos productos y cuántos descuentos hay, y la vista de una bodega distingue ambos.

Si además se quieren las tres tiendas y el comprador del seed opcional, ejecutar desde la raíz:

```powershell
$env:BODESMART_DEMO_SEED = "1"
python apps/backend/seed_customer_demo.py
```

Eso agrega tiendas, ofertas vigentes y un comprador demo sin sobrescribir jefes, empleados ni precios. Las credenciales quedan en `.demo-credentials.json` (ignorado por Git). También sirve la cuenta `cliente.demo@bodesmart.local` / `DemoCliente2026!` creada por `ensure_demo_sales()`.

## Flujo de compra

1. `/customer/offers` publica ofertas vigentes; `available` ya descuenta las reservas activas.
2. La cesta solo admite productos de una bodega y permite elegir entre **Pago local de prueba** y **Mercado Pago de prueba**. `GET /customer/payment-methods` publica ambos (sin exponer credenciales) y marca Mercado Pago como disponible solo cuando el backend tiene `MERCADOPAGO_ACCESS_TOKEN`. Si acabas de cargar la variable, recrea el backend antes de volver a la cesta; el procedimiento está en [apps/backend/README.md](../backend/README.md#habilitar-mercado-pago-de-prueba).
3. `POST /customer/orders` crea una reserva de diez minutos con UUID idempotente y guarda el método elegido en `Pago`; **no descuenta stock**. `Simular pago` aprueba `LOCAL_SIMULATION`; con Mercado Pago, `checkout` abre la pasarela de prueba y `verify-payment` consulta al proveedor desde el backend.
4. Solo la aprobación verificada descuenta stock. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` se muestran en `Mis pedidos` y nunca descuentan inventario.

No hay modo de compra local ni catálogo de ejemplo: si el backend no responde, la tienda muestra un error y no permite simular una compra. Toda reserva, aprobación y descuento de stock ocurre en el backend; la app del jefe recarga ventas e inventario al volver a la pestaña. El pago es de prueba, pero la venta y el movimiento de inventario son reales en la base local.

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

La sección `Perfil` reutiliza la misma tarjeta de la esquina inferior izquierda (avatar con inicial, nombre corto, rol `Cliente` y los tres puntos); en móvil se alcanza desde «Mi cuenta» en el panel desplegable. Los datos de la cuenta, el conteo de pedidos pagados y «Cerrar sesión» quedan en tarjetas separadas debajo.
