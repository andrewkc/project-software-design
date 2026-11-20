# admin-web

## Estado

Planificada, sin implementar. La carpeta solo contiene `.gitkeep`.

## Cómo funcionará

Aplicación interna para personal de BodeSmart. Servirá para consultar y gestionar cuentas de los roles jefe, empleado y cliente desde una tabla, con operaciones de creación, edición, activación y desactivación. Se publicará en `admin.bodesmart.com`.

El administrador de plataforma gestiona el acceso a la aplicación. No crea empleados de bodega: esa responsabilidad es del jefe en el MVP, según ADR-001. El rol administrador quedó fuera del primer corte del backend.

## Comandos de instalación y arranque

No hay comandos todavía. No ejecutes `npm install` ni otros comandos de build porque no existe `package.json`, código fuente ni stack definido.

Cuando se implemente, este README debe indicar:

- runtime y gestor de dependencias;
- comando de instalación;
- comando de desarrollo y URL local;
- comando de build y directorio de salida;
- variables de entorno y dirección de la API.

Las decisiones de framework, autenticación, contrato de API y despliegue siguen pendientes. No se deben asumir en silencio.

## Referencias

- [CU-01 Administrar cuentas y accesos](../../docs/02-business/use-cases/cases/CU-01.md)
- [RF-01 y RF-19](../../docs/03-requirements/functional-requirements.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [Preguntas abiertas 19 a 21](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)
