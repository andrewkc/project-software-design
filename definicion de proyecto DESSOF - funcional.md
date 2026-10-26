# Definición de proyecto DESSOF — alcance funcional

Versión 1.0 · 26 de octubre de 2026 · Estado: definición para prototipo; no implica implementación ni validación.

## 1. Visión y objetivo

Aplicación web de ofertas de alimentos próximos a vencer para varias bodegas. El comprador explora ofertas de una bodega, hace una compra de prueba mediante Mercado Pago Checkout Pro y recibe información para recoger en tienda. El dueño controla inventario por lotes y precios; un modelo de aprendizaje automático (ML) estima demanda y propone descuentos. El dueño puede mantener la revisión manual o activar expresamente el modo automático con límites definidos. La demo muestra tres bodegas; no procesa dinero real.

La interfaz existente en React es el punto de partida visual. El comportamiento actual del repositorio es un prototipo local; ninguna operación de su `localStorage` constituye inventario o pago oficial. El servidor y PostgreSQL serán la fuente de verdad.

## 2. Decisiones de alcance

| Tema | Decisión |
| --- | --- |
| Tiendas | Varias bodegas independientes; tres en la carga inicial. Una cesta y un pedido pertenecen a una sola tienda. |
| Perfiles | Administrador, dueño, empleado y cliente. Una cuenta de personal pertenece a una tienda; un dueño activo por tienda. |
| Productos | Alimentos de vida corta o media con duración declarada mínima de 7 días entre ingreso y vencimiento bajo sus condiciones de conservación; no platos preparados. Esta duración no es una certificación sanitaria. |
| Cantidades | Por lote, en gramos enteros o unidades enteras. Los lotes del mismo producto pueden tener cantidades y vencimientos diferentes. Venta en múltiplos de un paso configurado. |
| Stock | Único saldo compartido para ventas presenciales y web. Las reservas reducen disponibilidad, no stock físico. |
| Pago | Checkout Pro externo con credenciales y tarjetas de prueba. Al verificarse pago aprobado, el pedido se considera completado para la demo y se descuenta stock. |
| Recojo | Solo recojo en bodega; mensaje informativo de dirección, horario y tiempo estimado. Sin estado de entrega, confirmación de recojo ni gestión comercial de no recogidos o devoluciones. |
| ML | Modelo entrenado inicialmente con datos sintéticos separados de la tienda demo. Predice demanda; una política decide si conviene recomendar un descuento. |
| Automatización | `REVISION` por defecto. Solo el dueño activa `AUTOMATICO`, configura límites por oferta y puede volver a revisión. |
| Chatbot | Consulta de solo lectura, con respuestas y datos filtrados por rol. No calcula descuentos ni modifica registros. |

## 3. Fuera del MVP

Reparto, repartidores, carrito multitienda, pasarela con dinero real, liquidación a bodegas, facturación, contabilidad, proveedores, sugerencias de reposición, devoluciones comerciales, confirmación de recojo, OCR, registro automático por foto o voz, sensores y predicción de inocuidad. La foto de catálogo sí es opcional. No se promete que el ML reduzca pérdidas reales: la primera evaluación usa datos simulados.

Los fallos técnicos de pago, red o duplicación sí deben controlarse para preservar inventario, aunque no se presenten como flujo comercial de devoluciones.

## 4. Actores y permisos

| Capacidad | Administrador | Dueño | Empleado | Cliente |
| --- | --- | --- | --- | --- |
| Crear/desactivar tiendas y cuentas | Plataforma | Personal de su tienda | No | Su perfil |
| Crear productos, lotes e ingresos | No por defecto | Sí | No | No |
| Consultar inventario interno | No por defecto | Su tienda | Su tienda | Solo oferta pública |
| Venta presencial | No | Sí | Sí | No |
| Merma, ajuste y corrección | No | Sí | No | No |
| Configurar precios, límites y modo automático | No | Sí | No | No |
| Ver recomendaciones | No | Su tienda | Consulta limitada | No |
| Comprar por web | Cuenta cliente separada | Cuenta cliente separada | Cuenta cliente separada | Sí |
| Chatbot | Sin acceso administrativo | Datos autorizados de su tienda | Datos sin costo ni margen | Ofertas públicas |

Desactivar una cuenta conserva historial. El administrador no recibe por defecto acceso a costos, ventas o conversaciones privadas de bodegas. El servidor comprueba rol y tienda en cada operación.

## 5. Recorridos y casos de uso

| ID | Caso de uso | Actor principal | Resultado |
| --- | --- | --- | --- |
| CU-01 | Administrar cuentas y tiendas | Administrador | Cuenta o tienda creada, actualizada o desactivada con auditoría. |
| CU-02 | Gestionar personal | Dueño | Empleado asignado o retirado sin borrar movimientos previos. |
| CU-03 | Gestionar catálogo y lotes | Dueño | Producto y lote registrados con paso, costo, cantidad, conservación y vencimiento. |
| CU-04 | Registrar ingreso | Dueño | Movimiento confirmado incrementa físico del lote una vez. |
| CU-05 | Registrar venta presencial | Dueño o empleado | Se asignan lotes aptos por vencimiento, se calcula total y se descuenta físico en una transacción. |
| CU-06 | Registrar merma o ajuste | Dueño | Saldo corregido con motivo, responsable e historial; sin consumir reservas. |
| CU-07 | Consultar inventario e historial | Dueño o empleado | Saldo físico, reservado y disponible, vencimientos y movimientos de su tienda. |
| CU-08 | Explorar ofertas | Público | Oferta publicada muestra precio por paso, cantidad, vencimiento, bodega y condiciones. |
| CU-09 | Armar cesta e iniciar pedido | Cliente autenticado | Pedido de una tienda, total y precio congelados; reserva temporal completa o ninguna. |
| CU-10 | Pagar compra de prueba | Cliente | Redirección a Mercado Pago; el backend verifica aprobación y crea venta web exactamente una vez. |
| CU-11 | Consultar resultado | Cliente | Número, importe, estado verificado y recojo informativo; incidencias técnicas se muestran con claridad. |
| CU-12 | Configurar ofertas y límites | Dueño | Oferta publicada/pausada, piso de precio y descuento máximo registrados. |
| CU-13 | Analizar y decidir precio | Dueño | Recomendación de mantener o bajar, explicación y decisión auditada. En automático se aplica solo si el dueño lo habilitó y sigue dentro de límites. |
| CU-14 | Consultar chatbot | Cliente, dueño o empleado | Respuesta de solo lectura usando datos permitidos y vigentes. |

### 5.1 Compra web: flujo principal

1. Cliente ve catálogo sin cuenta; inicia sesión para pagar. La cesta solo contiene ofertas de una tienda y no reserva stock.
2. Al crear pedido, servidor comprueba publicación, vigencia, múltiplos, precio, horario y saldo; congela líneas e importe y reserva todas las cantidades o ninguna.
3. Backend crea una `order` de Checkout Pro en entorno de pruebas y entrega su `checkout_url`. El comprador usa únicamente medios de prueba.
4. El retorno del navegador muestra «verificando» hasta que el servidor consulta y valida la operación externa. El retorno por sí solo no acredita pago.
5. Ante aprobación válida y reserva vigente, servidor consume la reserva, descuenta físico, registra venta web y marca pedido `PAGADO` en una sola transacción. Para la demo se asume recojo y el flujo comercial termina aquí; no existe transición a `ENTREGADO`.

Reserva inicial: 10 minutos, limitada también por cierre de venta del lote. Resultado incierto puede mantenerla temporalmente en `VERIFICANDO`. Rechazo o expiración comprobada libera reserva. Aprobación tardía después de liberarla queda en `PAGO_EN_REVISION`; nunca toma stock de otro pedido ni simula una venta. No se implementa reembolso.

### 5.2 Inventario y caducidad

- Producto define unidad base (`G` o `UNIDAD`) y paso de venta. Por ejemplo, paso 250 g permite 250, 500 y 750 g; rechaza 300 g. No se mezclan unidades.
- Lote define código, ingreso, vencimiento, costo total y cantidad recibida. Un segundo lote del mismo producto puede tener otra cantidad, costo y vencimiento. El saldo del producto es la suma de sus lotes.
- La fecha de vencimiento es obligatoria. Cierre web y presencial por defecto: 23:59:59 del día anterior al vencimiento, hora de Lima; el dueño puede cerrar antes. Un lote vencido o deteriorado no se vende.
- Disponibilidad = físico − reservado. Sobrantes menores al paso siguen en inventario, pero no se ofrecen como paso entero.
- Venta presencial asigna primero lotes aptos con cierre más próximo. La web compra una oferta/lote explícito. Ingresos, ventas, mermas y ajustes generan movimientos inmutables con responsable y fecha.
- Una corrección crea un movimiento compensatorio enlazado al original. No reescribe cobros ni historia.

### 5.3 Precios y recomendaciones

- Cada lote publicado tiene oferta propia: precio original fijado al publicarla, precio actual, descuento máximo, piso y estado.
- El modelo estima ventas futuras en pasos por día a precios candidatos. El motor de decisión compara cobertura esperada del stock hasta cierre; no trata «días restantes» como un descuento aprendido.
- Objetivo inicial: vender al menos 90 % del stock disponible esperado antes del cierre. Si el precio actual ya lo consigue, se mantiene. En otro caso se elige el mayor precio candidato que alcance el objetivo; si ninguno lo alcanza, el de mayor venta esperada, con desempate por ingreso. Solo se recomienda bajar si la cobertura mejora al menos 5 puntos porcentuales.
- Precio propuesto > 0, nunca mayor al actual ni menor al piso autorizado. El piso efectivo respeta precio mínimo, descuento máximo y costo por paso, salvo autorización expresa del dueño para vender bajo costo.
- `REVISION` es el estado inicial. El dueño acepta, modifica dentro de límites o rechaza. Para activar `AUTOMATICO`, confirma globalmente el modo y configura límites completos para ofertas elegibles. La recomendación automática se aplica solo con modelo marcado `VALIDADO_DEMO`; una edición manual del precio pausa automatización de ese lote hasta liberación expresa.
- Todo análisis conserva versión del modelo, entradas, predicciones comparadas, explicación, precio anterior/nuevo, actor u origen automático y hora. Pedidos ya reservados mantienen su precio congelado.

### 5.4 Chatbot

Cliente: ofertas, pasos, precios, dirección y horario públicos. Empleado: stock, ventas y vencimientos de su tienda, sin costo ni margen. Dueño: datos autorizados de su tienda y explicación de recomendaciones. Solo lectura: no registra ventas, no modifica precios y no ejecuta SQL libre. Si Gemini no está disponible, la aplicación informa indisponibilidad y los flujos de inventario y compra siguen funcionando.

## 6. Reglas de negocio

| ID | Regla |
| --- | --- |
| RN-01 | Solo el dueño administra catálogo, lotes, ingresos, mermas, ajustes y política de precios de su tienda. |
| RN-02 | Empleado vende presencialmente y consulta su tienda, sin costos ni márgenes. |
| RN-03 | Cliente solo consulta ofertas públicas y sus propios pedidos. |
| RN-04 | Toda salida usa cantidad positiva en múltiplos del paso y saldo disponible suficiente; jamás deja físico menor que reservado. |
| RN-05 | Lote cerrado, vencido, pausado o no apto no se vende. |
| RN-06 | Pedido web pertenece a una sola tienda; servidor calcula y congela su total en PEN. |
| RN-07 | Stock web disminuye una sola vez tras aprobación externa verificada; eventos repetidos son idempotentes. |
| RN-08 | Ninguna recomendación se aplica fuera del piso o encima del precio actual; solo dueño activa automático. |
| RN-09 | Una oferta de un lote identifica claramente cantidad, precio por paso y vencimiento. |
| RN-10 | Datos privados de una tienda nunca se muestran o modifican desde otra. |
| RN-11 | Producto demo cumple duración declarada de al menos 7 días desde ingreso hasta vencimiento; puede quedarle menos de 7 días al momento de mostrar la oferta. |

## 7. Pantallas mínimas

Catálogo y detalle público; registro/acceso; cesta y checkout; resultado e historial de pedidos del cliente; panel de tienda; catálogo y lotes; ingreso; venta presencial; merma/ajuste; inventario e historial; ofertas y recomendaciones; límites y modo de precios; chatbot; administración de cuentas/tiendas. Diseño adaptable a móvil y escritorio. La interfaz debe identificar claramente los pagos y datos ficticios como «demo / prueba».

## 8. Datos iniciales de demostración

Tres tiendas ficticias: Mercado Verde, Dulce y Fresco, y Despensa Cercana; cuatro productos por tienda, un dueño y un empleado por tienda, un administrador y dos clientes. La fecha `D` es la fecha local de carga en America/Lima. Las fechas se materializan una vez; no se desplazan cada día. Cada fila genera un lote inicial con ingreso confirmado y modo `REVISION`.

| Tienda | Producto | Unidad/paso | Físico inicial | Duración total declarada | Días restantes en D | Precio original por paso (S/) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Mercado Verde | Almendras | G/250 | 5000 g | 30 días | 20 | 10,00 |
| Mercado Verde | Pasas | G/250 | 3000 g | 20 días | 12 | 6,00 |
| Mercado Verde | Fresas | G/250 | 2000 g | 7 días | 2 | 5,00 |
| Mercado Verde | Manzanas | G/500 | 6000 g | 10 días | 5 | 5,00 |
| Dulce y Fresco | Pastel entero | UNIDAD/1 | 6 | 7 días | 2 | 20,00 |
| Dulce y Fresco | Nueces | G/250 | 4000 g | 30 días | 15 | 12,00 |
| Dulce y Fresco | Arándanos | G/125 | 1000 g | 7 días | 3 | 6,00 |
| Dulce y Fresco | Uvas | G/500 | 4000 g | 7 días | 4 | 7,00 |
| Despensa Cercana | Plátanos | G/500 | 5000 g | 7 días | 3 | 4,00 |
| Despensa Cercana | Mangos | UNIDAD/1 | 12 | 7 días | 4 | 4,00 |
| Despensa Cercana | Dátiles | G/250 | 2000 g | 30 días | 18 | 9,00 |
| Despensa Cercana | Queque entero | UNIDAD/1 | 8 | 7 días | 2 | 14,00 |

`vencimiento = D + días restantes`; `ingreso = vencimiento − duración total`. Las duraciones son supuestos de demo que el equipo debe validar para productos concretos y condiciones de conservación antes de usar datos reales. Para demostrar lotes variables, agregar al menos un segundo lote de un producto por tienda con cantidad y vencimiento distintos; todo saldo nace de un ingreso registrado, no de editar una cifra. Cargar costos y límites ficticios de modo reproducible, sin activar autorización bajo costo por defecto.

## 9. Criterios de aceptación del MVP

1. Tres tiendas aisladas: una no accede a datos internos de otra; cliente solo ve ofertas públicas y sus pedidos.
2. Dos lotes de un mismo producto admiten cantidades y fechas diferentes; la venta respeta paso, vigencia y reservas.
3. Dos compras o ventas simultáneas por la última unidad permiten solo una confirmación; nunca hay saldo negativo.
4. Checkout Pro en pruebas completa compra aprobada sin dinero real; servidor verifica importe, moneda, identidad y estado; descuenta stock una vez. Rechazo, duplicado y aprobación tardía no crean venta falsa.
5. El dueño puede activar/desactivar automático; sin activación permanece en revisión. Precio nunca sube automáticamente ni cae por debajo del piso autorizado.
6. Informe reproducible de ML compara modelo, demanda histórica y regla simple; se informa si ML no mejora. Un modelo experimental no aplica precios automáticamente.
7. Chatbot no divulga costo/margen al empleado ni información de tienda ajena; no escribe datos. Su fallo no bloquea compra o venta.
8. El frontend React completa los recorridos con datos de API, sin depender de `localStorage` para stock, precio, cuenta o pedido.

## 10. Orden de construcción

Modelo y reglas → autenticación/tiendas → catálogo, lotes e inventario → venta presencial → ofertas, cesta, reserva y pago simulado local → asistente local de solo lectura → ML y evaluación → política automática → Mercado Pago de pruebas y Gemini → pruebas integrales. Las dependencias externas se integran en la fase 4; el pago simulado de la fase 3 no acredita una integración real.

## 11. Dependencias pendientes de implementación

El titular debe crear la aplicación de Mercado Pago y entregar credenciales **de prueba** mediante variables locales; para la familia Checkout Pro Orders la documentación vigente permite pagar con tarjeta de prueba sin cuenta comprador externa. El flujo de webhook requiere una URL HTTPS accesible o, durante desarrollo, conciliación desde el servidor. El acceso y la cuota gratuita de Gemini también se comprueban en la cuenta antes de activar el chatbot. Ninguna integración se considera terminada solo por estar descrita.

Referencias de pago: [credenciales de prueba](https://www.mercadopago.com.pe/developers/es/docs/checkout-pro-orders/create-application), [compra de prueba](https://www.mercadopago.com.pe/developers/es/docs/checkout-pro-orders/integration-test/test-purchase-with-card).
