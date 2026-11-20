# BodeSmart API

Primer corte del backend. Expone una API REST para autenticación, perfiles de jefe y empleado, productos y movimientos de inventario. Está basado en ADR-003 y no está conectado todavía a `operations-web`, que sigue usando su persistencia local.

## Entorno virtual

Todas las dependencias se instalan en `.venv`, dentro de esta carpeta. No instales paquetes de forma global.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Si PowerShell bloquea la activación, ejecuta antes `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. Para producción, usa `requirements.txt` en lugar de `requirements-dev.txt`.

## Ejecutar

Con el entorno activado, desde `apps/backend`:

```bash
uvicorn main:app --reload
```

La documentación interactiva queda en `http://localhost:8000/docs`.

Pruebas:

```bash
python -m pytest -q
```

Para salir del entorno: `deactivate`.

Variables de entorno:

- `BODEGA_DB_PATH`: ruta al archivo SQLite. Por defecto `apps/backend/bodega.db`.
- `BODEGA_CORS_ORIGINS`: orígenes permitidos separados por coma. Por defecto `http://localhost:5173`.

## Autenticación

Todas las rutas excepto `/health`, `/auth/signup` y `/auth/login` requieren la cabecera:

```
Authorization: Bearer <token>
```

El token se obtiene al iniciar sesión y se guarda en la tabla `sessions`. Revocar un empleado invalida sus tokens.

## Rutas

| Método | Ruta | Acceso | Descripción |
| --- | --- | --- | --- |
| GET | `/health` | público | Estado del servicio |
| POST | `/auth/signup` | público | Crea un perfil jefe y devuelve token |
| POST | `/auth/login` | público | Verifica correo, contraseña y estado |
| GET | `/auth/me` | autenticado | Perfil actual |
| POST | `/auth/change-password` | autenticado | Cambia la contraseña propia |
| GET | `/profiles/employees` | jefe | Empleados de su bodega |
| POST | `/profiles/employees` | jefe | Crea empleado con contraseña inicial |
| POST | `/profiles/employees/{id}/revoke` | jefe | Revoca acceso y bloquea sus filas |
| GET | `/products` | autenticado | Productos de su bodega |
| POST | `/products` | autenticado | Crea producto y su lote inicial |
| PATCH | `/products/{id}` | según propiedad y bloqueo | Edita producto; si cambia stock, registra ajuste |
| POST | `/products/{id}/lock` | jefe | Bloquea o desbloquea una fila |
| POST | `/products/{id}/deactivate` | jefe | Desactiva o reactiva sin borrar historial |
| GET | `/movements` | jefe | Movimientos de su bodega, solo lectura |
| POST | `/movements` | autenticado | Registra entrada o salida de forma atómica |

## Reglas aplicadas

- Cada usuario opera solo sobre su bodega.
- El jefe edita cualquier fila, incluidas las bloqueadas; el empleado solo edita filas activas, desbloqueadas y creadas por él.
- El jefe desactiva en lugar de eliminar. Revocar un empleado conserva su historial y bloquea sus filas.
- Toda salida exige lote, cantidad positiva y responsable. Se rechaza si no hay stock o si el lote está vencido. No hay salidas parciales.
- Un ajuste directo de stock genera un movimiento con responsable y valores anterior y nuevo. Su lote queda pendiente de decisión (pregunta abierta 11).
- Las contraseñas se guardan hasheadas con bcrypt. Nunca se devuelven en la API.

## Pendiente

Conexión con `operations-web`, migración a PostgreSQL, estados de deterioro, catálogos de estado, moneda y precisión, unidades fraccionarias, selección de lote FIFO o FEFO, umbral de vencimiento y sugerencias de IA. Estos puntos siguen como preguntas abiertas en `docs/03-requirements/open-questions.md`.

## Referencias

- [Requisitos funcionales RF-15 a RF-19 y RF-23](../../docs/03-requirements/functional-requirements.md)
- [Casos de uso CU-01 a CU-07](../../docs/02-business/use-cases/README.md)
- [Reglas de negocio RN-01 a RN-11](../../docs/02-business/business-rules.md)
- [Entidades EN-01 a EN-08](../../docs/02-business/entities.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [ADR-003 Backend del primer corte](../../docs/04-architecture/decisions/ADR-003-backend-primer-corte.md)
- [Preguntas abiertas](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)

