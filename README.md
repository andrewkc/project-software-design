# BodeSmart

<p align="center">
  <img src="apps/operations-web/src/assets/BodeSmart-Logo.png" alt="Logo de BodeSmart" width="320">
</p>

BodeSmart es una propuesta de aplicación para bodegas y minimarkets de barrio. Busca reemplazar el control de existencias en papel, tickets y memoria por registros sencillos y consultables.

El trabajo se apoya en entrevistas exploratorias. Esas entrevistas describen el problema, pero no demuestran que la herramienta reduzca pérdidas ni que sus recomendaciones sean acertadas. Esta documentación describe un MVP propuesto, no un producto terminado.

## El problema

Las bodegas entrevistadas no saben con certeza qué stock tienen. Los ingresos se anotan en cuadernos o documentos, las salidas se recuerdan o se apoyan en tickets, y los vencimientos se revisan de forma informal. Cuando aparece un problema, cuesta saber quién registró cada movimiento.

## Lo que propone BodeSmart

- Registrar entradas de mercadería ya recibida y salidas por venta o merma.
- Consultar inventario, existencias por lote y fechas de vencimiento.
- Identificar al responsable de cada movimiento.
- Supervisar el trabajo del personal desde una sola vista.
- Definir precios y promociones de uso interno.
- Recibir sugerencias de reposición y descuentos, siempre sujetas a la decisión del jefe.

La IA apoya la decisión. Nunca aprueba promociones, genera compras ni modifica el inventario por su cuenta.

## Quiénes lo usan

**Jefe de bodega.** Ve y administra toda su bodega. Puede bloquear filas, desactivar productos sin borrar el historial, fijar precios y aprobar promociones o sugerencias.

**Empleado.** Trabaja solo en la bodega asignada. Registra entradas y salidas, edita únicamente las filas que creó y no puede eliminarlas ni desactivarlas.

**Administrador interno.** Perfil previsto para la app de administración. Gestiona altas, cambios y bajas de cuentas de jefes, empleados y clientes. Esta app está planificada y aún no está implementada.

**Comprador.** Destinatario de la tienda pública prevista. Queda fuera del MVP documentado.

## Las aplicaciones previstas

| App | Dominio | Estado |
| --- | --- | --- |
| operations-web | app.bodesmart.com | Prototipo actual para jefe y empleado |
| admin-web | admin.bodesmart.com | Planificada, sin implementar |
| customer-web | bodesmart.com | Planificada, fuera del MVP |
| backend | No expuesto públicamente | Primer corte en curso: auth, perfiles, productos y movimientos |
| database | No expuesto públicamente | Planificada, sin implementar |

El prototipo de operations-web ya cubre el registro de productos, el inventario con ID por fila, el bloqueo y la desactivación, la creación de empleados con contraseña generada y la persistencia de perfiles en SQLite dentro del navegador. Las reglas de roles, propiedad y bloqueo, y la persistencia en SQLite están registradas como decisiones propuestas y aplicadas al prototipo. No son requisitos aprobados para producción.

## Lo que queda fuera del MVP

No se incluyen proveedores, pagos, facturación electrónica, entregas, contabilidad, estimación de vida útil por IA ni vista de compradores. El prototipo muestra pantallas de ejemplo para registro por foto, código, texto y voz, pero esas modalidades no forman parte del MVP documentado.

## Cómo se construye la documentación

Trabajamos por funcionalidad con el ciclo Descubrir, Especificar, Revisar, Planear, Tareas, Implementar, Validar y Aprender. Cada funcionalidad mantiene trazabilidad entre casos de uso, requisitos, reglas de negocio, entidades, pruebas y código.

Las afirmaciones se etiquetan como confirmadas, derivadas, propuestas o pendientes. Ante una contradicción, se registra como pregunta abierta o decisión de arquitectura. No se decide en silencio.

## Estado de certeza

- Confirmado: lo que dicen las entrevistas y la fuente original.
- Propuesto: reglas de roles, propiedad y bloqueo, y persistencia de perfiles en SQLite. Aplicadas solo al prototipo.
- Pendiente: arquitectura de producción, despliegue, proveedor de IA, métricas no funcionales y varias preguntas de negocio todavía abiertas.
