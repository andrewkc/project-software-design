# DESSOF · demo local de bodegas

Fases 1 y 2: base de datos, cuentas, tres tiendas de muestra, 12 productos, 15 lotes y gestión real de bodega. La pantalla original de React sigue siendo un prototipo visual separado; entra en **Gestión real de bodega** para usar productos, lotes, ingresos, ventas presenciales, mermas, ajustes y ofertas conectados a PostgreSQL. Las compras web, reservas, ML, chatbot y Mercado Pago se implementan en las fases siguientes.

## Estructura

```text
backend/       Django: modelos, servicios transaccionales, API y pruebas
frontend/      React/Vite existente y panel de gestión real
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

La API expone sesión y tiendas (`/api/v1/auth/*`, `/api/v1/stores`) y rutas internas bajo `/api/v1/store/*` para productos, lotes, ingresos, ventas locales, mermas, ajustes, movimientos y ofertas. Solo el dueño puede ingresar stock, ajustar y modificar ofertas; el empleado registra ventas y consulta sin ver costos. Login y demás escrituras requieren CSRF; los datos de sesión se mantienen en cookie HttpOnly. Las operaciones de stock usan claves de idempotencia y bloqueos de PostgreSQL.

Los documentos de alcance y arquitectura están un nivel arriba, en los dos archivos `definicion de proyecto DESSOF - *.md`.
