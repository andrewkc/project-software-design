# ADR-007: `customer-web` full-stack y pago de prueba en el MVP ampliado

**Estado:** Aceptado por el usuario el 2026-11-26. Pidió una aplicación de clientes con la misma identidad visual que `operations-web`, datos que salgan de la base actual del repositorio, integración con el backend y el flujo de checkout/pago de prueba de la implementación de su compañero. Rechazó explícitamente una interfaz solo de demostración y la opción de «no pagar». La ampliación de alcance está aprobada; la implementación queda pendiente de ejecutar `pytest`, `npm run build` y validación en navegador porque el shell del entorno está bloqueado.

**Fecha:** 2026-11-26

## Contexto

El alcance de `scope.md` excluía la vista pública y los pagos. ADR-006 ya había preparado el esquema (`Oferta`, `Compra`, `DetalleCompra`, `Pago`, `ReservaCompra`) y el contrato transaccional `POST /sales`, pero dejaba la autenticación del comprador y la tienda para otro corte.

El proyecto companion de `C:\projects-4\project-software-design` contiene un `customer-web` con catálogo, cesta, pedidos reservados y checkout de Mercado Pago de prueba, además de `routers/customer.py`, `seed_customer_demo.py` y `tests/test_customer_flow.py`. Ese código se toma como **referencia**, no como copia: su interfaz usa otra paleta, tipografía demasiado pequeña, navegación móvil incompleta, estilos muertos en el hero y un historial que oculta los pedidos no pagados. Su seed además reescribe contraseñas de jefe/empleado/cliente y crea un segundo jefe con `id_bodega` ya ocupado.

La base actual ya tiene todas las tablas y columnas necesarias: `apps/database/database.sql` y las migraciones de `ensure_schema()` cubren el contrato de reservas, idempotencia y pago. No había que importar SQL del companion.

## Decisión

- Incorporar `customer-web` como aplicación del MVP ampliado. Se reutilizan los tokens visuales exactos de `operations-web` (`--ink`, `--muted`, `--green`, `--green-dark`, `--green-soft`, `--line`, `--cream`, `--font-scale: 1.4` en el resto de la tienda y `1.2` en el acceso de escritorio), DM Sans/Manrope, el patrón de barra lateral y el layout de perfil con rol `Cliente`. La navegación móvil era una barra inferior de cuatro secciones; ADR-009 la sustituye por un menú desplegable de hamburguesa con las cuatro secciones y «Mi cuenta». Menú: `Inicio`, `Bodegas`, `Mi cesta`, `Mis pedidos`; el perfil se abre desde la tarjeta de cuenta. Se conservan los textos `Bodegas y ofertas`, `Tu cesta`, `Mis pedidos`, `Pagar con Mercado Pago de prueba`, `Simular pago` y `Comprobar estado`; el aviso de acceso de prueba se retiró del login por solicitud del producto para mantener una presentación profesional.
- Actualización posterior (petición del producto, no hallazgo de entrevista): la entrada `Perfil` se retiró del menú de `customer-web` y de `admin-web` porque la tarjeta de cuenta de la esquina inferior izquierda ya abre la misma página; ADR-009 añade «Mi cuenta» al panel móvil porque el sidebar está oculto. La barra inferior pasó a cuatro secciones en cliente y tres en administración, y luego fue reemplazada por el menú desplegable de hamburguesa. El acceso usa escala `1.2` en escritorio (antes `1.08`) con márgenes compactos para no requerir scroll, y el logo interno no dibuja borde ni fondo de botón.
- Actualización posterior (integración real): se retiró el modo de exploración local. Si la API no responde, la tienda muestra un error; nunca inventa bodegas ni crea pedidos en memoria. Toda compra nace en `POST /customer/orders` y solo se confirma cuando el backend aprueba el pago. `operations-web` recarga `/sales` y `/products` al recuperar el foco y cada 15 s, además del botón «Actualizar», para que el historial del jefe y el inventario dejen de depender de la instantánea del login.
- Actualización posterior (pasarela visible): la cesta ofrece dos métodos con tarjetas diferenciadas —`LOCAL_SIMULATION` y `MERCADOPAGO_TEST`. `GET /customer/payment-methods` solo publica etiquetas y disponibilidad, nunca la clave. El método elegido viaja en `POST /customer/orders` (la UI siempre lo envía), se guarda en `Pago` y se devuelve en `payment_mode`, de modo que sobrevive a recargas; los clientes antiguos que omiten el campo conservan el comportamiento previo; `checkout()` solo abre la URL que devuelve el backend. Si no hay token de prueba, la opción aparece deshabilitada con la explicación correspondiente.
- Mantener `VITE_API_BASE_URL || http://127.0.0.1:8000` y el token `bodesmart_customer_token`. El frontend solo llama a `/customer/*`; la aprobación del pago nunca depende de lo que envíe el navegador.
- Portar `routers/customer.py` al backend actual con los mismos contratos (`/stores`, `/payment-methods`, `/offers`, `/auth/register|login|me`, `/orders`, `/orders/{id}`, `/orders/{id}/simulate-payment`, `/orders/{id}/checkout`, `/orders/{id}/verify-payment`, `/payments/webhook`). Registrar el router en `main.py` y ampliar CORS a `5173`/`5174` en `localhost` y `127.0.0.1`.
- Unificar el descuento de inventario: `sales_service.py` expone `decrement_stock_once()` y `approve_reserved_order()`. Tanto `create_paid_sale()` (usado por `POST /sales` y por las compras demo) como el checkout del cliente pasan por esa única regla con `UPDATE ... WHERE stock >= cantidad RETURNING stock` dentro de la transacción. El router del cliente no contiene su propio `UPDATE ... SET stock`.
- Reserva de diez minutos. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` no descuentan stock. Un pago acreditado después de vencer la reserva se marca `pago_en_revision` para revisión humana, sin tocar inventario. La aprobación idempotente impide un segundo descuento.
- Incluir pagos de prueba: simulación local (`LOCAL_SIMULATION`) y checkout de Mercado Pago de prueba (`MERCADOPAGO_TEST`) con validación server-side de importe, referencia, moneda, cuenta y URL de retorno; webhook firmado HMAC. Son credenciales de prueba y una demo académica, no cobro real. `ALLOW_SIMULATED_PAYMENT` permite desactivar la simulación.
- El historial del cliente muestra **todos** los estados, no solo `pagado`, para poder reanudar una reserva y entender por qué el stock no cambió. `Ventas` en `operations-web` sigue mostrando solo compras pagadas: ambas reglas son deliberadamente distintas.
- El seed opcional `seed_customer_demo.py` solo agrega tiendas, ofertas vigentes y un comprador propio (`cliente.tienda@bodesmart.local`) con credenciales generadas en un archivo ignorado. No toca jefes, empleados, contraseñas, precios ni ofertas existentes, y no resucita stock vencido o deteriorado. `cliente.demo@bodesmart.local` sigue perteneciendo a `ensure_demo_sales()` con su contraseña conocida.

## Consecuencias

- Se mantiene la trazabilidad de ADR-006: no se crean `Movimiento`/`DetalleMovimiento`, no se amplía a proveedores, pagos reales, facturación, delivery, contabilidad ni estimación de vida útil por IA.
- El esquema de `apps/database` no se sobrescribe con el SQL del companion; el seed es complementario y está detrás de `BODESMART_DEMO_SEED=1`.
- Las pruebas de integración `tests/test_customer_flow.py` requieren `BODESMART_TEST_DATABASE_URL` igual a `DATABASE_URL` para evitar accidentes sobre una base real. Las comprobaciones estáticas (`tests/test_customer_contract.py`, `tests/test_endpoint_usage.py`) no necesitan base.
- El shell de Windows está fallando con `OS Error -1073283067` al intentar lanzar `pwsh`; por eso no se pudo ejecutar `npm install`, `npm run build`, `pytest` ni una comprobación en navegador. Los cambios quedan como implementación propuesta y verificable en cuanto el entorno responda.

## Contradicciones registradas, no resueltas en silencio

- `scope.md` decía «sin vista pública» y «sin pasarela externa»; el usuario aprobó la ampliación a full-stack con pago de prueba. El texto de exclusión se actualiza, pero sigue excluyendo pagos **reales**.
- La referencia del companion ofrecía un modo demo sin backend y una opción de «no pagar» como camino principal; el usuario las rechazó. Ambas se retiraron por completo: sin backend no hay catálogo ni checkout, y la UI muestra el error en lugar de datos o pedidos inventados.
- `Jefe.id_bodega` es único y la bodega sembrada ya está asignada; por eso el seed portado no crea dueño ni empleado.
- El companion ocultaba pedidos no pagados; aquí se muestran todos, mientras `GET /sales` mantiene su filtro de solo pagados.
- Las direcciones de las tiendas del seed son datos de demostración derivados, no información de entrevistas; se escriben solo sobre campos vacíos.

## Alternativas descartadas

- **Copiar el `customer-web` del companion tal cual:** otra paleta, textos pequeños, navegación móvil incompleta y contradicciones con el backend actual. Descartada.
- **Sobrescribir la base con el SQL del companion:** el esquema actual ya contiene las tablas; habría destruido datos. Descartada.
- **Reutilizar el seed del companion sin cambios:** cambiaba contraseñas y podía violar `Jefe.id_bodega UNIQUE`. Descartada.
- **Dejar que el navegador confirme el pago:** permitiría descontar stock sin verificación del proveedor. Descartada por RN-04.
