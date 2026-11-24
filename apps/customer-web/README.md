# customer-web

Frontend de BodeSmart para jefe, empleado y cliente. Parte de una copia de `operations-web`, que se mantiene como guía visual y no se modifica aquí.

## Estado

Prototipo funcional en el navegador. **Todavía no está conectado al backend**: productos, ventas y cuentas se guardan en `localStorage`, `sessionStorage` y SQLite del navegador, igual que en `operations-web`.

## Ejecutar

Requiere Node LTS. Desde esta carpeta:

```bash
npm install
npm run dev     # http://127.0.0.1:5174
npm test
npm run build
```

En desarrollo, la pantalla de ingreso tiene accesos **Jefe**, **Empleado** y **Cliente** con cuentas ficticias. No aparecen en el build de producción.

Para ver el stock en vivo, abre dos pestañas: una como **Cliente** y otra como **Empleado**, y registra una venta.

## Qué agrega a operations-web

| Función | Comportamiento |
| --- | --- |
| Registrar ventas (CU-05) | Cesta con total y responsable. Rechaza toda la venta si un producto está vencido, desactivado o sin stock suficiente, y descuenta una sola vez. |
| Cuenta cliente | Registro vinculado a una bodega. Solo ve productos vendibles, con stock, precio y disponibilidad; no ve autor, candados ni pantallas internas. |
| Stock en vivo | Los cuadros cambian sin recargar y marcan la diferencia. Hoy funciona entre pestañas del mismo navegador. |
| Voz | Dictado con Web Speech API (`es-PE`) para registrar productos y armar ventas. Si el navegador no lo soporta, se puede escribir la frase. |
| Cámara | Foto o galería y lectura de etiqueta con OCR (Tesseract.js): nombre, precio y vencimiento. También lee códigos de barras donde exista `BarcodeDetector`. |

La IA solo sugiere. Toda sugerencia queda en el formulario o la cesta y una persona debe confirmarla.

**Privacidad:** en Chrome, el dictado envía el audio al servicio de voz del navegador. El OCR corre en el dispositivo, pero descarga su motor y el idioma español la primera vez.

## Pendiente de backend

La API actual cubre auth, perfiles, productos y movimientos. Para conectar esta app falta:

1. Rol `cliente` y su registro; hoy `/auth/signup` solo crea jefes.
2. Catálogo de solo lectura para clientes, limitado a su bodega y sin datos internos.
3. Listar lotes por producto: `POST /movements` exige `loteId` en salidas y no hay ruta para obtenerlo. El front usa un lote implícito `INICIAL`.
4. Canal en vivo (WebSocket o SSE) para reemplazar `subscribeToKeys` en `src/lib/liveStock.js`.
5. Campo `barcode` en productos.
6. Lectura de ventas para el empleado: `GET /movements` hoy es solo para jefe.

## Alcance por aprobar

`AGENTS.md` y `docs/01-product/scope.md` dejan fuera del MVP la vista de compradores y el registro por voz o fotografía. Esta rama los implementa a pedido del equipo, así que el cambio de alcance debe registrarse y aprobarse en la documentación.

## Referencias

- [Alcance del MVP](../../docs/01-product/scope.md)
- [Requisitos funcionales](../../docs/03-requirements/functional-requirements.md)
- [Reglas de negocio](../../docs/02-business/business-rules.md)
- [README del backend](../backend/README.md)
