# Plan técnico — VENTAS-01

**Estado:** Aceptado por el usuario. Implementado en código, esquema, migraciones, demo e interfaz. **Pendiente:** `pytest`, `npm run build`, reconstrucción de contenedores y validación en navegador.

## Enfoque propuesto

Reutilizar el contrato de compras que el compañero implementó en su `customer-web` sin copiar su servicio de pagos ni su autenticación. Una sola función de servicio (`sales_service.create_paid_sale`) crea la compra pagada y descuenta el stock en la transacción que administra el router. El listado (`GET /sales`) y el alta (`POST /sales`) comparten la misma definición de venta y el mismo `sale_response`, de modo que la UI no puede mostrar una operación que el inventario no respalda. Las compras demo se siembran desde el arranque con claves fijas y savepoints: si la base ya existía, se migran las columnas y se insertan las tres compras sin duplicar descuentos.

## Componentes afectados

| Capa | Archivo | Cambio |
|---|---|---|
| Esquema base | `apps/database/database.sql` | Columnas `Oferta.id_bodega`/`.precio_original`, `Compra.reserva_hasta`/`.idempotency_key`/`.request_hash`/`.fecha_pago`, `DetalleCompra.id_oferta`, columnas de proveedor en `Pago`, tabla `ReservaCompra` e índice parcial. |
| Seed | `apps/database/seed.sql` | Aclaración de que las compras se siembran desde el backend para bases ya creadas. |
| Migraciones y arrange | `apps/backend/database.py` | `ALTER TABLE ... IF NOT EXISTS` para las columnas nuevas, creación de `ReservaCompra`, helpers de categorías y llamada a `ensure_demo_sales(conn)`. |
| Servicio de compra | `apps/backend/sales_service.py` | `create_paid_sale`, `release_expired`, `sale_response`, `ensure_demo_sales`, validaciones y descuento atómico. |
| API | `apps/backend/routers/sales.py` | `GET /sales` y `POST /sales` con filtro por `bodega_id_for` y rol jefe/empleado. |
| Arranque | `apps/backend/main.py` | Registro del router de ventas. |
| Seguridad | `apps/backend/security.py` | Sin cambios; se reutilizan `fail`, `require`, `identity_from_header` y `hash_password`. |
| Cliente HTTP | `apps/operations-web/src/lib/api.js` | `listSales()` y `createSale(payload)`. |
| Navegación | `apps/operations-web/src/data/demoData.js` | Entrada `sales` en `navigation` y `mobileNavigation` sin `jefeOnly`/`empleadoOnly`. |
| Estado | `apps/operations-web/src/App.jsx` | Carga de `sales` en el `Promise.all` inicial y render de `SalesPage`. |
| Página | `apps/operations-web/src/features/sales/SalesPage.jsx` | Resumen, lista de compras, líneas y estado vacío; solo lectura. |
| Estilos | `apps/operations-web/src/styles.css` | Tarjetas de resumen, compra, líneas y adaptación móvil. |
| Pruebas | `tests/test_sales.py`, `tests/test_backend_api.py`, `tests/test_endpoint_usage.py` | Contrato estático, permisos, bodega, solo `pagado`, idempotencia y no doble descuento. |
| Documentación | ADR-006, RF-31…RF-33, RN-15/RN-16, trazabilidad, READMEs y esta carpeta | Registro de decisión, requisitos, reglas y validación pendiente. |

## Contratos / interfaces

### `GET /sales`

- Autenticación: `Authorization: Bearer <token>`; solo `jefe` o `empleado`.
- Respuesta: arreglo de compras pagadas de la bodega del token.

```json
[
  {
    "id": 1,
    "estado": "pagado",
    "cliente": "Cliente Demo",
    "clienteId": 1,
    "bodegaId": 1,
    "fechaCompra": "2026-11-26T15:00:00",
    "fechaPago": "2026-11-26T15:00:00",
    "total": "18.00",
    "metodoPago": "LOCAL_SIMULATION",
    "lineas": [
      {
        "id": 1,
        "productoId": 13,
        "ofertaId": null,
        "nombre": "Manzana roja",
        "icono": "🍎",
        "unidad": "kg",
        "cantidad": 4,
        "precioUnitario": "4.50",
        "subtotal": "18.00"
      }
    ]
  }
]
```

### `POST /sales`

```json
{
  "id_cliente": 1,
  "lineas": [
    { "id_producto": 13, "cantidad": 4, "id_oferta": null }
  ],
  "idempotency_key": "11111111-1111-4111-8111-111111111111"
}
```

`id_oferta` e `idempotency_key` son opcionales. La respuesta es el objeto de compra del listado. Cualquier error revierte la transacción completa.

## Decisiones de implementación

- **Una sola definición de venta:** `estado = 'pagado'`. La lectura filtra por ese estado; la escritura lo fija al insertar.
- **Stock agregado por bodega:** se usa `ProductosBodega.stock` como en el backend revisado. No se crean lotes ni movimientos en este corte.
- **Bloqueo y descuento condicional:** `SELECT ... FOR UPDATE OF pb` y `UPDATE ... WHERE stock >= cantidad RETURNING stock`. Si el `UPDATE` no devuelve fila, se falla y se revierte.
- **Idempotencia:** UUID + `pg_advisory_xact_lock` + `request_hash` para devolver la compra previa o rechazar un payload distinto con la misma clave.
- **Demo en arranque, no en `seed.sql`:** `ensure_schema()` corre sobre bases creadas antes de estos cambios. Cada compra usa una clave fija y un savepoint para no duplicar descuentos ni romper el arranque si el usuario editó el producto.
- **UI de solo lectura:** no hay botones de cobro, edición ni anulación; `createSale` quedó disponible en `api.js` como contrato y ahora es usado por `customer-web` (ADR-007) a través del servicio compartido de descuento.
- **Privacidad mínima:** se envía `nombres apellidos`; no se exponen correo ni teléfono.

## Seguridad y cumplimiento

- El token se valida en cada petición y `bodega_id_for` limita la lectura y escritura a una bodega.
- No se usa `GEMINI_API_KEY` ni se envían datos a proveedores externos. El pago es solo una traza local (`LOCAL_SIMULATION`).
- No se usan datos reales de clientes: la demo usa un correo reservado para el prototipo.
- La IA no genera compras ni modifica inventario por sugerencia; tampoco interviene en `Ventas`.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Doble descuento al reiniciar | Claves de idempotencia fijas + consulta previa + savepoint por demo. |
| Stock insuficiente por concurrencia | `FOR UPDATE OF pb` y actualización condicional con `RETURNING`. |
| Historial inconsistente | La misma función escribe la compra y descuenta; la lectura solo filtra pagadas. |
| Columnas ausentes en base antigua | Migraciones `IF NOT EXISTS` en `ensure_schema()`. |
| Demo con producto editado | Excepción controlada por compra; el resto se siembra y la UI explica el estado vacío. |
| Filtrado de bodega ausente | `bodega_id_for` se llama antes de consultar o insertar. |

## Validación pendiente

1. Ejecutar `pytest` con `apps\backend\.venv` para los archivos de registro, backend, recomendaciones, ventas y endpoints.
2. Ejecutar `npm run build` en `apps\operations-web`.
3. Reconstruir imagen local con `docker compose up -d --build backend operations-web` (sin `down -v`).
4. Verificar `/health`, login jefe y empleado, sección `Ventas`, stock descontado una sola vez y reinicio sin duplicados.
