# DESSOF · demo local de bodegas

Fases 1 a 3: base de datos, cuentas, tres tiendas de muestra, 12 productos, 15 lotes, gestión real de bodega y compra local simulada. Entra en **Gestión real de bodega** para gestionar inventario y en **Comprar en bodegas** para ver ofertas, armar una cesta, reservar y simular un pago. La pantalla original sigue siendo un prototipo visual separado. Mercado Pago, Gemini y el modelo de ML quedan para la fase 4; esta fase no usa dinero ni servicios externos.

## Estructura

```text
backend/       Django: modelos, servicios transaccionales, API y pruebas
frontend/      React/Vite, panel de gestión y panel de comprador
compose.yaml   PostgreSQL 16 local
```

## Iniciar en PowerShell

Requisitos: Python 3.12 o versión compatible con Django 5.2, Node.js, npm y Docker Desktop. Desde esta carpeta:

```powershell
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\manage.py migrate
$env:DESSOF_DEMO_PASSWORD = 'UnaClaveLocalDe12CaracteresOMas!'
python backend\manage.py seed_demo
python backend\manage.py runserver
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Vite envía `/api` a `http://127.0.0.1:8000`. Las cuentas demo usan direcciones `@demo.example` (`admin`, `dueno.1` a `dueno.3`, `empleado.1` a `empleado.3`, `cliente.1` y `cliente.2`) y la contraseña indicada solo en tu entorno local. Cambia esa clave si compartes la base. `seed_demo` solo funciona en una base sin tiendas y se niega a duplicar datos.

## Comprobación

```powershell
python -m pytest -q
python backend\manage.py check
cd frontend
npm test
npm run build
```

Las pruebas de Python usan PostgreSQL real, no SQLite. Para una base distinta, configura `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` y `POSTGRES_PORT`. Los secretos y dependencias locales están ignorados por Git.

La API expone sesión y registro de compradores (`/api/v1/auth/*`), tiendas, ofertas públicas (`/api/v1/offers`), pedidos (`/api/v1/orders`), pago **simulado local** (`/api/v1/orders/{id}/simulate-payment`) y asistente local de solo lectura (`/api/v1/chat`). Las rutas `/api/v1/store/*` permiten gestionar inventario y ofertas. Solo el dueño puede ingresar stock, ajustar y modificar ofertas; el empleado registra ventas y consulta sin ver costos. Login y demás escrituras requieren CSRF; los datos de sesión se mantienen en cookie HttpOnly. Pedidos y movimientos usan claves de idempotencia y bloqueos de PostgreSQL. Un pedido reserva por hasta 10 minutos; una aprobación local consume la reserva y descuenta inventario una sola vez; rechazo o vencimiento la libera. La aprobación simulada no prueba la integración con Mercado Pago.

Los documentos de alcance y arquitectura están un nivel arriba, en los dos archivos `definicion de proyecto DESSOF - *.md`.
