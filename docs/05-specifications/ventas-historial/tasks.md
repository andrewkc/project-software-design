# Tareas — VENTAS-01

**Estado:** Implementadas en prototipo. **Pendiente de verificación:** ejecución de pruebas, compilación frontend, reconstrucción local y validación en navegador.

## Discover

- [x] Revisar la navegación y los permisos actuales de `operations-web`: no existía `Ventas`.
- [x] Revisar `customer-web` del compañero: `/customer/orders` solo muestra pedidos `pagado`.
- [x] Revisar `customer.py` de referencia: el único descuento de stock ocurre en `_approve`, en la misma transacción que consume reservas y marca la compra como `pagado`.
- [x] Revisar las tablas nuevas de referencia en el checkout del compañero.
- [x] Confirmar con el usuario el uso de esas tablas, datos demo y trazabilidad limitada a `Compra` + descuento atómico, sin `Movimiento`/`DetalleMovimiento`.

## Specify

- [x] Definir `VENTAS-01` como ampliación de CU-05 y CU-07 sin renombrar identificadores existentes.
- [x] Agregar RF-31…RF-33 y RN-15/RN-16 con trazabilidad en `functional-requirements.md`, `business-rules.md` y `traceability.md`.
- [x] Registrar la decisión en ADR-006 y las preguntas abiertas en `open-questions.md`.
- [x] Escribir `spec.md` y `plan.md` de la funcionalidad.

## Review

- [x] Comprobar que solo `pagado` cuenta como venta y que reservas activas no descuentan stock.
- [x] Verificar que no se amplía el MVP con pasarela, pagos reales ni interfaz de comprador.
- [x] Revisar que los datos demo sean sintéticos y no usen información real de clientes.
- [ ] Validar con el usuario la política de privacidad del nombre del comprador y la posible vista de pedidos no pagados (preguntas abiertas).

## Plan

- [x] Elegir un servicio compartido para alta y lectura con una sola definición de venta.
- [x] Definir migraciones idempotentes para bases ya creadas.
- [x] Definir idempotencia UUID, bloqueo de filas y descuento condicional.
- [x] Definir siembra demo desde arranque con savepoints y claves fijas.
- [x] Definir la UI de solo lectura y su estado vacío.

## Tasks (código)

- [x] Actualizar `apps/database/database.sql` y `apps/database/seed.sql`.
- [x] Crear `apps/backend/sales_service.py` con validación, descuento atómico, idempotencia, respuesta y demo.
- [x] Agregar migraciones y `ensure_demo_sales(conn)` en `apps/backend/database.py`.
- [x] Crear `apps/backend/routers/sales.py` y registrarlo en `apps/backend/main.py`.
- [x] Agregar `listSales`/`createSale` en `apps/operations-web/src/lib/api.js`.
- [x] Agregar `Ventas` a `navigation` y `mobileNavigation` en `demoData.js`.
- [x] Crear `apps/operations-web/src/features/sales/SalesPage.jsx`.
- [x] Conectar `App.jsx` y agregar estilos en `styles.css`.
- [x] Actualizar READMEs de raíz, backend, database, operations-web y quality.
- [ ] Crear/ajustar `tests/test_sales.py` y `tests/test_endpoint_usage.py`.

## Implement

- [x] Carga inicial de ventas tolerante a error (`catch(() => [])`) para no bloquear inventario ni perfiles.
- [x] Filtro por bodega del token antes de leer o escribir.
- [x] Rollback completo ante cualquier validación fallida.
- [x] Siembra demo con savepoint por compra para no romper el arranque.

## Validate

- [ ] `& "C:\projects\project-software-design\apps\backend\.venv\Scripts\python.exe" -m pytest tests/test_registration_ai.py tests/test_backend_api.py tests/test_ai_recommendations.py tests/test_sales.py tests/test_endpoint_usage.py -q`
- [ ] `cd apps\operations-web; npm run build`
- [ ] `docker compose up -d --build backend operations-web` (sin `down -v`).
- [ ] Comprobar `/health` en `127.0.0.1:8000` y el frontend en `127.0.0.1:5173`.
- [ ] Iniciar sesión como jefe y como empleado; confirmar que `Ventas` aparece para ambos.
- [ ] Confirmar que el stock de los productos demo bajó una sola vez y que un reinicio no lo baja de nuevo.
- [ ] Confirmar que no se expone `GEMINI_API_KEY` en el bundle del navegador.

## Learn

- [ ] Registrar resultados reales en `docs/06-quality/README.md`.
- [ ] Actualizar preguntas abiertas con cualquier discrepancia encontrada en la validación.
- [ ] No afirmar que el producto está terminado ni que reduce pérdidas: las entrevistas siguen siendo exploratorias.
