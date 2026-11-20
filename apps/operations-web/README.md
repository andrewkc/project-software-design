# BodegaSmart — prototipo frontend de operaciones

Prototipo adaptable a escritorio y móvil para la gestión interna de una bodega. Es la app que usan el **jefe** y el **empleado** en `app.bodesmart.com`. Toda la información se guarda en el navegador: los perfiles en SQLite dentro del navegador (`sql.js`) y el resto en `localStorage`. No hay backend conectado todavía.

## Ejecutar

Desde esta carpeta:

```bash
npm install
npm run dev
```

Para comprobar la compilación de producción:

```bash
npm run build
```

## Cómo funciona

- **Acceso:** registro de jefe con nombres y apellidos separados, e inicio de sesión con correo y contraseña. El jefe crea cuentas de empleado con una contraseña inicial generada, puede revocar el acceso y permite al empleado cambiar su contraseña. Revocar conserva el historial y bloquea las filas del empleado.
- **Roles:** el jefe edita cualquier fila, incluidas las bloqueadas, y puede bloquear, desactivar y reactivar productos sin borrarlos. El empleado edita solo filas activas, desbloqueadas y creadas por él, incluido precio y stock, y accede únicamente a su bodega asignada.
- **Inventario:** alta de productos con icono emoji, búsqueda, ID por fila, autor de cada registro y edición en línea. Toda edición directa de stock deja un movimiento de ajuste con responsable y valores anterior y nuevo.
- **Alertas y sugerencias:** vencimientos calculados desde las fechas ingresadas y propuestas demostrativas de descuento y reposición que la persona puede revisar, ajustar o descartar. La IA solo apoya la decisión; nunca aprueba por sí sola ni modifica el inventario.
- **Registro de mercadería:** flujos demostrativos de foto, voz, escritura y código de barras. El navegador permite elegir o tomar una foto; voz, escaneo, análisis de imágenes y predicciones de IA no están conectados a servicios reales.
- **Hallazgos:** pantalla con control de memoria o papel, dificultad para registrar ventas, pérdidas por vencimiento y necesidad de identificar al responsable de cada movimiento.

Las decisiones de roles, propiedad y bloqueo, y la persistencia de perfiles son propuestas aplicadas al prototipo, no requisitos aprobados para producción. Las entrevistas son exploratorias: el prototipo no demuestra reducción de pérdidas ni efectividad de la IA.

## Referencias

- [Visión del producto](../../docs/01-product/vision.md)
- [Alcance del MVP](../../docs/01-product/scope.md)
- [Requisitos funcionales RF-15 a RF-22](../../docs/03-requirements/functional-requirements.md)
- [Casos de uso CU-01 a CU-09](../../docs/02-business/use-cases/README.md)
- [Reglas de negocio RN-10 y RN-11](../../docs/02-business/business-rules.md)
- [ADR-001 Roles, propiedad de filas y candado](../../docs/04-architecture/decisions/ADR-001-roles-propiedad-bloqueo.md)
- [ADR-002 Persistencia de perfiles con SQLite](../../docs/04-architecture/decisions/ADR-002-persistencia-perfiles-sqlite.md)
- [Preguntas abiertas](../../docs/03-requirements/open-questions.md)
- [README raíz](../../README.md)
