# database

## Estado

Esquema base en `database.sql` y datos iniciales en `seed.sql`. El contenedor aplica ambos en orden durante la inicialización de PostgreSQL.

El inventario está separado del catálogo:

- `Producto`: catálogo (`id`, `icono`, `nombre`, `categoria`, `unidad_medida`).
- `ProductosBodega`: inventario por bodega (`id_producto`, `id_bodega`, `stock`, `precio_venta`, `fecha_vencimiento`, `estado`), con PK compuesta `(id_producto, id_bodega)` y FK a `Producto` y `Bodega`.
- `Categoria`: catálogo persistente de categorías (`nombre VARCHAR(100) PRIMARY KEY`, `fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP`). `Producto.categoria` guarda el nombre de una sola categoría como relación lógica, no FK física (RN-14/RF-29).
- `Cliente`, `Oferta`, `Compra`, `DetalleCompra`, `Pago` y `ReservaCompra`: contrato de compras tomado como referencia del `customer-web` implementado por el compañero. `Compra.estado = 'pagado'` es la única venta: el stock se descuenta en la misma transacción en que se guarda la compra. Las reservas activas sirven para disponibilidad, no para el historial de ventas.

## Qué pobla el seed

- `Bodega San Martín` con id 1. La dirección queda vacía porque no fue proporcionada.
- No se siembra ningún jefe ni contraseña. La cuenta se crea desde `/auth/signup`, que guarda el password con bcrypt.
- Los 26 productos de `starterProducts` en `../../operations-web/src/data/demoData.js` como catálogo.
- Las 26 filas de `ProductosBodega` para la bodega 1, con stock, precio y vencimiento. Los productos sin fecha quedaron con `fecha_vencimiento = NULL`.
- Nueve categorías base: Abarrotes, Lácteos, Frutas, Bebidas, Limpieza, Snacks, Conservas, Cuidado personal y Otros. Son las mismas nueve que usa la UI y el fallback `CATEGORIAS` de `registration_ai.py`.
- No crea empleados.
- No inserta compras: `sales_service.ensure_demo_sales()` del backend siembra tres compras pagadas sintéticas con claves fijas y descuenta stock una sola vez. Así también funciona en una base ya creada.

El script es idempotente: usa `ON CONFLICT DO NOTHING` y ajusta las secuencias `SERIAL` al final. Si la base ya tenía categorías en `Producto`, el backend `ensure_schema()` crea `Categoria` si falta, migra esos nombres con `SELECT DISTINCT ON (clave) nombre` sobre `lower(btrim(categoria))` (deduplicación insensible a mayúsculas/minúsculas) y siembra las nueve base. Las categorías nuevas se crean desde `POST /categories`; se reutilizan por nombre sin FK física.

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
- `creadoPor`, `bloqueado` y `bloqueadoPor` de ADR-001 aún no están en el esquema base; `ensure_schema()` los agrega.
- Fuera del esquema base: tablas de movimientos, sesiones y lotes. Las interfaces de `customer-web` y `admin-web` existen como aplicaciones propias y consumen el contrato transaccional de compras y el catálogo `/admin/*` ya presentes en el backend y en estas tablas.

## Referencias

- [Esquema base](database.sql)
- [Seed](seed.sql)
- [Entidades EN-01 a EN-08](../../docs/02-business/entities.md)
- [Reglas de negocio](../../docs/02-business/business-rules.md)
- [Modelo de dominio](../../docs/04-architecture/domain-model.md)
- [ADR-001 Roles, propiedad y bloqueo](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [ADR-003 Backend del primer corte](../../docs/04-architecture/decisions/ADR-003-backend-primer-corte.md)
- [ADR-005 Registro asistido por foto, código y voz](../../docs/04-architecture/decisions/ADR-005-registro-asistido-por-ia.md)
- [ADR-006 Historial de ventas y compra atómica](../../docs/04-architecture/decisions/ADR-006-ventas-historial-compra-atomica.md)
- [REG-IA](../../docs/05-specifications/registro-asistido-ia/spec.md)
- [Preguntas abiertas 9 a 13 y 23](../../docs/03-requirements/open-questions.md)
