# database

## Estado

Reservada, sin esquema aplicado. `schema.sql` y `01_create_database.sql` solo contienen marcadores, y `scripts/` está vacío.

## Cómo funcionará

Esta carpeta está prevista para el esquema y las migraciones versionadas del modelo de datos. Debe conservar trazabilidad con las entidades EN-01 a EN-08 y con las reglas de negocio RN-01 a RN-11.

Hoy el backend no consume esta carpeta. `apps/backend` crea su propia base SQLite local en `apps/backend/bodega.db` desde el código de ADR-003. La migración a PostgreSQL está prevista, pero no implementada. ADR-002 describe una persistencia distinta: SQLite dentro del navegador, usada solo por el prototipo `operations-web`.

## Comandos de instalación y arranque

No hay comandos válidos todavía. No ejecutes los archivos `.sql` de esta carpeta porque aún no definen tablas ni migraciones.

Si quieres inspeccionar la base local que crea el backend, puedes hacerlo desde esta carpeta:

```bash
sqlite3 ../backend/bodega.db
```

Ese archivo se genera al iniciar el backend. No es una base de producción.

Cuando el esquema esté listo, este README debe indicar el motor soportado, el orden de las migraciones, el comando para aplicarlas y la política de respaldo.

## Referencias

- [Entidades EN-01 a EN-08](../../docs/02-business/entities.md)
- [Reglas de negocio](../../docs/02-business/business-rules.md)
- [Modelo de dominio](../../docs/04-architecture/domain-model.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [ADR-003 Backend del primer corte](../../docs/04-architecture/decisions/ADR-003-backend-primer-corte.md)
- [Preguntas abiertas 9 a 13 y 23](../../docs/03-requirements/open-questions.md)
