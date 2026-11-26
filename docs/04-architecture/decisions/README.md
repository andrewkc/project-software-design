# ADR

Decisiones técnicas y de modelo registradas durante la especificación.

| ADR | Tema | Estado |
|---|---|---|
| [ADR-001](ADR-001-roles-propiedad-bloqueo.md) | Roles, propiedad de filas y candado de edición | Propuesto / aplicado en el prototipo `operations-web` |
| [ADR-002](ADR-002-persistencia-perfiles-sqlite.md) | Persistencia de perfiles con SQLite | Propuesto / aplicado en el prototipo `operations-web` |
| [ADR-003](ADR-003-backend-primer-corte.md) | Backend del primer corte | Aprobado por el usuario para el primer corte de `apps/backend` |
| [ADR-004](ADR-004-gemini-recomendaciones-ia.md) | Gemini para recomendaciones IA | Aceptado por el usuario para el prototipo; modelo y cuota pendientes |
| [ADR-005](ADR-005-registro-asistido-por-ia.md) | Registro asistido por foto, código y voz | Aceptado y ampliado el 2026-11-26: voz transcribe todos los campos dictados sin estimar vencimiento, botón de cámara alterno, emojis amplios con paridad y categorías persistentes; `v1beta` corregido tras `400`; `Código` usa Open Food Facts tras `429`; selector de modelo con allowlist tras `503` por alta demanda; pruebas y validación real pendientes |
| [ADR-006](ADR-006-ventas-historial-compra-atomica.md) | Historial de ventas y compra atómica | Aceptado el 2026-11-26: `Ventas` para jefe y empleado, `Compra.estado = 'pagado'` como única venta, descuento atómico de stock con idempotencia, tablas tomadas del `customer-web` del compañero y tres compras demo sintéticas; pruebas y validación real pendientes |
| [ADR-007](ADR-007-cliente-web-pago-prueba.md) | `customer-web` full-stack y pago de prueba | Aceptado el 2026-11-26: interfaz de cliente con la identidad visual de `operations-web`, mismos datos y descuento atómico, reserva de diez minutos, checkout/pago de prueba y seed no destructivo; contradicciones del companion registradas; pruebas, build y validación en navegador pendientes por shell bloqueado |
| [ADR-008](ADR-008-admin-web-alcance-cuentas.md) | Alcance del panel administrativo sobre cuentas | Aceptado el 2026-11-26: admin gestiona los cuatro roles, no puede modificar/desactivar a otro admin, baja lógica y endpoints `/admin/*` aislados; supera parcialmente ADR-001 solo para `admin-web`; pruebas, build y validación pendientes |
| [ADR-009](ADR-009-shell-movil-favicon.md) | Shell móvil y favicon compartido | Solicitado el 2026-11-26 e implementado como propuesta en las tres apps: hamburguesa inferior con panel desplegable, sin barra fija de muchas secciones, tipografía legible y `/favicon.png`; pendiente de revisión visual, build y pruebas |

No había decisiones arquitectónicas aprobadas en el entregable inicial.
