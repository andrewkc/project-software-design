# database

## Estado

Esquema base en `database.sql` y datos iniciales en `seed.sql`. El contenedor aplica ambos en orden durante la inicialización de PostgreSQL.

El inventario está separado del catálogo:

- `Producto`: catálogo (`id`, `icono`, `nombre`, `categoria`, `unidad_medida`).
- `ProductosBodega`: inventario por bodega (`id_producto`, `id_bodega`, `stock`, `precio_venta`, `fecha_vencimiento`, `estado`), con PK compuesta `(id_producto, id_bodega)` y FK a `Producto` y `Bodega`.

## Qué pobla el seed

- `Bodega San Martín` con id 1. La dirección queda vacía porque no fue proporcionada.
- No se siembra ningún jefe ni contraseña. La cuenta se crea desde `/auth/signup`, que guarda el password con bcrypt.
- Los 26 productos de `starterProducts` en `../../operations-web/src/data/demoData.js` como catálogo.
- Las 26 filas de `ProductosBodega` para la bodega 1, con stock, precio y vencimiento. Los productos sin fecha quedaron con `fecha_vencimiento = NULL`.
- No crea empleados.

El script es idempotente: usa `ON CONFLICT DO NOTHING` y ajusta las secuencias `SERIAL` al final.

## Cómo ejecutarlo

Con Docker, `database.sql` se aplica como `01-database.sql` y `seed.sql` como `02-seed.sql`:

```bash
docker build -t bodesmart-database .
docker run -d --name database -e POSTGRES_PASSWORD=tu_password -p 5432:5432 bodesmart-database
```

Si la base ya existía con el esquema anterior, hay que reconstruirla o migrar `Producto` a catálogo antes de ejecutar:

```bash
psql -h localhost -U postgres -d postgres -f seed.sql
```

## Pendiente

- Dirección real de la bodega.
- Apellidos del jefe confirmados; los del seed se derivaron del correo.
- Contraseña hasheada.
- `creadoPor`, `bloqueado` y `bloqueadoPor` de ADR-001 aún no están en el esquema.
- Fuera de este corte: movimientos, sesiones, lotes, `customer-web` y `admin-web`.

## Referencias

- [Esquema base](database.sql)
- [Seed](seed.sql)
- [Entidades EN-01 a EN-08](../../docs/02-business/entities.md)
- [Reglas de negocio](../../docs/02-business/business-rules.md)
- [Modelo de dominio](../../docs/04-architecture/domain-model.md)
- [ADR-001 Roles, propiedad y bloqueo](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [ADR-003 Backend del primer corte](../../docs/04-architecture/decisions/ADR-003-backend-primer-corte.md)
- [Preguntas abiertas 9 a 13 y 23](../../docs/03-requirements/open-questions.md)
