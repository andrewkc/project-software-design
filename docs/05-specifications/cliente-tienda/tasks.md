# CLIENTE-01 — Tareas

| # | Tarea | Estado |
|---|---|---|
| 1 | Scaffold Vite/React: `package.json`, `index.html`, `main.jsx`, `App.jsx` | Implementado; build pendiente |
| 2 | Tokens y layout: `styles.css`, `Brand`, `Icon`, `CustomerLayout`, `PageDate`, `LayoutContext`, `navigation.js` | Implementado; validación visual pendiente |
| 3 | Vistas: `AuthScreen`, `HomePage`, `StoresPage`, `OfferCard`, `CatalogToolbar`, `CartPage`, `OrdersPage`, `ProfilePage` | Implementado; validación en navegador pendiente |
| 4 | Cliente API y utilidades: `api.js`, `format.js`, `catalog.js`, `demoData.js` | Implementado |
| 5 | Backend: `routers/customer.py`, registro en `main.py`, banderas y CORS en `config.py`, `.env.example` | Implementado; pruebas pendientes |
| 6 | Shared stock rule: `decrement_stock_once()` y `approve_reserved_order()` en `sales_service.py` | Implementado; `tests/test_sales.py` pendiente de ejecución |
| 7 | Seed opcional no destructivo y `.gitignore` de credenciales | Implementado |
| 8 | Pruebas: `tests/test_customer_contract.py`, `tests/test_customer_flow.py`, cobertura de endpoints en `test_endpoint_usage.py` | Escritas; ejecución bloqueada por shell |
| 9 | Documentación: `scope.md`, ADR-007, README raíz/backend/customer-web y esta spec | Implementado |
| 10 | Ejecutar `npm install`, `npm run build`, `pytest` y probar checkout en navegador | Bloqueado: `pwsh` no inicia (`OS Error -1073283067`) |
| 11 | Shell móvil ADR-009: favicon, hamburguesa desplegable, piso tipográfico y `tests/test_web_shell_contract.py` | Implementado como propuesta; validación visual y build pendientes |

## Cómo validar cuando el shell responda

```powershell
python -m pytest tests/test_sales.py tests/test_endpoint_usage.py tests/test_customer_contract.py -v
cd apps/customer-web; npm install; npm run build
```

Para el flujo completo con base desechable, seguir `tests/test_customer_flow.py`; el módulo se omite solo si no se define `BODESMART_TEST_DATABASE_URL` igual a `DATABASE_URL`.
