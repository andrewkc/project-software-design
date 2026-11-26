# Especificaciones por funcionalidad

Crear una carpeta por funcionalidad. El equipo no necesita especificar todo el sistema antes de iniciar: especificar, revisar, planificar y dividir en tareas de manera iterativa.

| Funcionalidad | Estado | Especificación |
|---|---|---|
| REC-IA — recomendaciones para decisión del jefe | Implementada en prototipo; pendiente de validación con Gemini | [spec.md](recomendaciones-ia/spec.md) · [plan.md](recomendaciones-ia/plan.md) · [tasks.md](recomendaciones-ia/tasks.md) |
| REG-IA — registro asistido por foto, código y voz | Implementada en prototipo, incluidas voz completa, cámara alterna, emojis amplios, categorías persistentes y selector de modelo con allowlist; pendiente de `pytest`, `npm run build` y validación multimodal real | [spec.md](registro-asistido-ia/spec.md) · [plan.md](registro-asistido-ia/plan.md) · [tasks.md](registro-asistido-ia/tasks.md) |
| VENTAS-01 — historial de ventas y compra atómica | Implementada en prototipo: `Ventas` para jefe y empleado, solo compras pagadas, descuento atómico de stock y tres compras demo sintéticas; pendiente de `pytest`, `npm run build` y validación en navegador | [spec.md](ventas-historial/spec.md) · [plan.md](ventas-historial/plan.md) · [tasks.md](ventas-historial/tasks.md) |
| CLIENTE-01 — tienda del comprador y pago de prueba | Implementada en prototipo con la identidad visual de `operations-web`, reserva de diez minutos, checkout de prueba y descuento compartido con `Ventas`; pendiente de `pytest`, `npm run build` y validación en navegador por shell bloqueado | [spec.md](cliente-tienda/spec.md) · [plan.md](cliente-tienda/plan.md) · [tasks.md](cliente-tienda/tasks.md) |
| ADMIN-01 — panel administrativo de cuentas y bodegas | Implementada en prototipo con endpoints `/admin/*` aislados, gestión de los cuatro roles, autoprotección entre admins e identidad visual de `operations-web`; pendiente de `pytest`, `npm run build` y validación en navegador | [spec.md](admin-web/spec.md) · [plan.md](admin-web/plan.md) · [tasks.md](admin-web/tasks.md) |
