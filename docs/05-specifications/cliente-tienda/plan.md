# CLIENTE-01 — Plan

**Estado:** Aceptado con ADR-007. Sigue el ciclo Descubrir → Especificar → Revisar → Planear → Tareas → Implementar → Validar → Aprender.

## Descubrir

- Revisar `operations-web` como fuente de tokens visuales, layout, menú y perfil.
- Revisar el `customer-web` y el backend del companion como referencia de contratos y flujo de pago, distinguiendo lo que se copia de lo que se corrige.
- Confirmar que el esquema actual ya contiene `Cliente`, `Oferta`, `Compra`, `DetalleCompra`, `Pago` y `ReservaCompra`; no importar SQL externo.

## Especificar y revisar

- Registrar la ampliación en `scope.md`, ADR-007 y esta especificación, con contradicciones explícitas, sin resolverlas en silencio.
- Definir la reserva de diez minutos, los estados visibles y la regla de «pago aprobado» como único descuento de stock.

## Planear

1. Crear el scaffold Vite/React de `customer-web` y sus componentes de layout con los tokens de `operations-web`.
2. Adaptar las vistas de catálogo, cesta, pedidos y perfil a la API `/customer/*`.
3. Portar el router del cliente al backend actual, con banderas de pago en `config.py` y CORS para `5174`.
4. Extraer la aprobación de reservas y el descuento a `sales_service.py` para compartirlos con `POST /sales`.
5. Agregar seed opcional no destructivo y credenciales generadas en un archivo ignorado por Git.
6. Cubrir con pruebas estáticas y de integración; actualizar README y trazabilidad.

## Tareas y validación

Ver `tasks.md`. La validación completa está bloqueada por el shell (`pwsh` falla con `OS Error -1073283067`): no se pudo ejecutar `npm install`, `npm run build`, `pytest` ni comprobar en navegador. Las verificaciones estáticas quedan registradas como pendientes de ejecución.

## Aprender

- La referencia del companion sirvió como contrato, no como implementación: su interfaz y su seed requerían correcciones.
- La duplicación de la regla de stock era el principal riesgo; concentrarla en `sales_service.py` evita que dos flujos descuenten de forma distinta.
- El historial del comprador y el de `Ventas` responden preguntas distintas; ocultar estados en la tienda dificultaba entender el inventario.
