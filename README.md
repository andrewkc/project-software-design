# DESSOF · demo local de bodegas

Fase 1: base de datos, cuentas, tres tiendas de muestra, 12 productos, 15 lotes y API básica. El frontend React original sigue siendo **visual**: todavía guarda su inventario de ejemplo en el navegador. Las ventas, reservas, ML, chatbot y Mercado Pago se implementan en las fases siguientes.

## Estructura

```text
backend/       Django: modelos, migraciones, API y pruebas
frontend/      React/Vite existente; cliente API inicial
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

La API inicial expone `GET /api/v1/health`, `GET /api/v1/stores`, `GET /api/v1/auth/csrf`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout` y `GET /api/v1/auth/me`. Login y demás escrituras requieren CSRF; los datos de sesión se mantienen en cookie HttpOnly.

Los documentos de alcance y arquitectura están un nivel arriba, en los dos archivos `definicion de proyecto DESSOF - *.md`.
