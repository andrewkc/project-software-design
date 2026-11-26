# Requisitos funcionales iniciales

**Derivados de casos de uso; revisar y convertir en criterios verificables.**

| ID | Requisito | Trazabilidad |
|---|---|---|
| RF-01 | Administrador crea, actualiza, activa y desactiva cuentas. | CU-01, RN-01 |
| RF-02 | Jefe mantiene datos de su bodega y catálogo. | CU-02, RN-02 |
| RF-03 | Jefe incorpora/retira empleados conservando registros históricos. | CU-03 |
| RF-04 | Registrar entradas por producto, lote, cantidad, costo y vencimiento cuando aplique. | CU-04, RN-03 |
| RF-05 | Registrar salidas por venta o merma. | CU-05 |
| RF-06 | Impedir salidas superiores al stock y descontar una sola vez. | CU-05, RN-04 |
| RF-07 | Calcular total con cantidad y precio aplicado. | CU-05, RN-05 |
| RF-08 | Impedir venta de productos vencidos/deteriorados. | CU-05, RN-06 |
| RF-09 | Consultar existencias por producto/lote y vencimientos registrados. | CU-06 |
| RF-10 | Jefe consulta movimientos y responsables sin alterarlos. | CU-07 |
| RF-11 | Jefe modifica precios y gestiona promociones. | CU-08, RN-07, RN-09 |
| RF-12 | Jefe revisa, modifica, aprueba o rechaza sugerencias IA de descuento y aumento de precio; la IA no aplica cambios por sí sola. | CU-08, RN-08, ADR-004 |
| RF-13 | Jefe revisa, modifica, aprueba o rechaza sugerencias de reposición. | CU-09, RN-08 |
| RF-14 | Aprobar reposición no genera compra ni modifica inventario. | CU-09, RN-08 |
| RF-15 | El jefe crea cuentas de empleado con contraseña inicial generada, entrega credenciales y revoca accesos conservando el historial. | CU-03, RN-02, ADR-001 (propuesto) |
| RF-16 | El empleado edita solo filas activas, no bloqueadas y creadas por él; no elimina ni desactiva. | CU-02, RN-10, ADR-001 (propuesto) |
| RF-17 | El jefe bloquea/desbloquea filas; una fila bloqueada solo la edita el jefe. | CU-02, RN-11, ADR-001 (propuesto) |
| RF-18 | El jefe desactiva productos conservando historial; un ajuste directo de stock registra responsable y valores anterior/nuevo. | CU-02, CU-07, RN-03, RN-11, ADR-001 (propuesto) |
| RF-19 | Los perfiles se persisten en SQLite: el login verifica correo, contraseña y estado; el registro y el alta de empleados insertan un registro único por correo. | CU-01, CU-03, ADR-002 (propuesto) |
| RF-20 | La interfaz adapta el lenguaje al rol: el jefe ve referencias a su bodega/inventario; el empleado ve la bodega asignada y el inventario de la bodega, sin presentarse como propietario. | CU-02, CU-03, RN-02, RN-10, ADR-001 (propuesto) |
| RF-21 | Junto al avatar circular de perfil se muestra siempre primer nombre y primer apellido, sin importar el rol; el nombre completo queda disponible en la página de perfil. | CU-01, CU-03, EN-01, ADR-001 (propuesto) |
| RF-22 | El inventario muestra el ID de cada fila y el autor como "Agregado por usted" o "Agregado por <nombre corto>"; el registro permite elegir el emoji del producto en cualquier modo. | CU-02, CU-04, EN-03, RN-03, RN-10, ADR-001 (propuesto) |
| RF-23 | El backend expone una API para autenticación, perfiles de jefe y empleado, productos y movimientos. Verifica correo, contraseña hasheada y estado, aísla cada bodega y aplica las reglas de propiedad, bloqueo y stock. | CU-01 a CU-07, RN-01 a RN-06, RN-10, RN-11, ADR-001, ADR-002, ADR-003 |
| RF-24 | El backend genera recomendaciones IA bajo demanda solo para el jefe, sin escribir en la base ni aplicar cambios; falla de forma controlada si el proveedor no está disponible. | CU-08, CU-09, RN-07, RN-08, ADR-004, REC-IA |
| RF-25 | El usuario registrador puede capturar una foto del producto y recibir un borrador IA con nombre, ícono, categoría, cantidad y unidad; precio y vencimiento siguen manuales. | CU-02, RN-12, ADR-005, REG-IA |
| RF-26 | El usuario registrador puede capturar/subir la imagen de un código de barras; el backend consulta Open Food Facts con los dígitos procesados y devuelve un borrador saneado, sin proponer cantidad ni precio/vencimiento. Si el código no está en la base, responde «No se encontró en la base de datos. Regístralo manualmente.» | CU-02, RN-12, RN-13, ADR-005, REG-IA |
| RF-27 | El usuario registrador puede grabar voz real y recibir un borrador que transcribe **todos** los campos dictados: nombre, ícono, categoría, cantidad, unidad, `precio_venta`, `fecha_vencimiento` y `codigo_barras` si se dictan dígitos. Precio y fecha se transcriben solo si se dicen explícitamente (fecha ISO `AAAA-MM-DD`); la IA no estima vida útil. | CU-02, RN-12, RN-13, ADR-005, REG-IA |
| RF-28 | Todos los campos propuestos o dictados son revisables en cualquier modo (texto, foto, código o voz); la IA no guarda productos, no crea movimientos ni modifica stock, y el alta ocurre solo cuando el usuario confirma el formulario existente. La creación explícita de categoría guarda solo el catálogo de categorías. | CU-02, CU-04, RN-03, RN-08, RN-14, ADR-005, REG-IA |
| RF-29 | El usuario puede consultar y ampliar un catálogo persistente de categorías desde el registro: buscador, opción «Agregar nueva categoría», reutilización insensible a mayúsculas/minúsculas y una sola categoría por producto. | CU-02, EN-03, RN-14, ADR-005, REG-IA |
| RF-30 | El selector de Ícono ofrece un conjunto amplio de emojis con keywords en frontend y backend; en `Código`, el botón del medio alterna entre usar la imagen del código enfocado y volver a encender la cámara, sin quitar «Subir imagen» ni «Leer dígitos». | CU-02, RN-12, ADR-005, REG-IA |
| RF-31 | Jefe y empleado consultan en `Ventas` el historial de compras pagadas de clientes de su bodega, con cliente, fecha de pago, total y detalle por producto con precios y cantidades congelados. | CU-05, CU-07, RN-02, RN-04, RN-05, RN-06, VENTAS-01 |
| RF-32 | El backend registra una compra pagada en una sola transacción: valida cliente activo, cantidades positivas, producto activo y no vencido, precio positivo, stock suficiente e idempotencia; descuenta stock una sola vez y guarda `Compra`, `DetalleCompra`, `ReservaCompra` consumida y traza de pago local. | CU-05, RN-03, RN-04, RN-05, RN-06, VENTAS-01 |
| RF-33 | Los estados que no descontaron stock (`pendiente`, `expirado`, `rechazado`, `pago_en_revision`) no se muestran como ventas; las compras demo son sintéticas y no usan datos reales de clientes. | CU-05, CU-07, RN-04, RN-06, VENTAS-01 |
| RF-34 | En `Foto` y `Voz`, el usuario registrador puede elegir entre los modelos Gemini autorizados por el backend; la selección se envía con la solicitud de extracción y no expone la clave ni acepta modelos arbitrarios del navegador. | CU-02, RN-17, ADR-005, REG-IA |

**Estado de RF-25…RF-30 y RF-34:** propuestos como requisitos verificables y aplicados al prototipo según ADR-005. RF-27/RN-13 dependen de la precisión real del dictado; RF-29/RN-14 dependen de la persistencia de `Categoria` y de la reutilización insensible a mayúsculas/minúsculas; RF-30 depende de la paridad exacta de emojis y del alternador de cámara. RF-34 está implementado con una allowlist del backend; cambiar de modelo no garantiza superar un `503` por alta demanda. La ejecución de pruebas y la validación real siguen pendientes en [docs/06-quality/README.md](../06-quality/README.md).

**Estado de RF-31…RF-33:** derivados de la revisión del `customer-web` del compañero y de las tablas que agregó; aplicados al prototipo según ADR-006 y VENTAS-01. El contrato de compra y el historial están implementados. ADR-007 agregó la interfaz de comprador, la autenticación de clientes y el pago de prueba con cabecera de RF-31…RF-33; la pasarela de cobro real sigue fuera del alcance.
