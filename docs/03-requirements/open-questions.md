# Preguntas abiertas

## Negocio
1. ¿Cuál es el umbral de “próximo a vencer”?
2. Si una salida tiene varios productos y uno no es apto, ¿se rechaza toda la operación o solo una línea?
3. ¿Cómo se selecciona lote cuando hay varios? No se define FIFO/FEFO.
4. ¿Cuáles son los catálogos de estado de cuenta, producto, promoción y sugerencia?
5. ¿Qué ocurre con acceso e historial cuando se retira un empleado?
6. ¿Se permiten varias promociones vigentes por producto?
7. ¿Cómo se resuelven cambios de precio entre resumen y confirmación?
8. ¿Qué datos mínimos exige una merma?

## Modelo
9. Reconciliar multiplicidades de cuenta/bodega con texto: cada bodega tiene un jefe y varios empleados; el jefe forma parte del personal.
10. Revisar relación jefe/revisor de sugerencias: el texto indica jefe responsable, el diagrama presenta muchos-a-muchos.
11. Confirmar obligatoriedad de lote por detalle.
12. Definir moneda y precisión de importes.
13. Definir cantidades fraccionarias y unidades.

## IA
14. ¿Qué historial mínimo habilita sugerencias?
15. ¿Qué método genera sugerencias? Parcialmente resuelta: Gemini para el prototipo (ADR-004); modelo definitivo pendiente.
16. ¿Cómo se explica la justificación? Parcialmente resuelta: frase breve basada en campos existentes; no es predicción validada.
17. ¿Cómo se mide utilidad/precisión/impacto?
18. ¿Qué ocurre si IA no está disponible? Parcialmente resuelta: `503` controlado; inventario y consultas siguen disponibles.

## Producto/operación
19. Dispositivos y navegadores soportados.
20. Funcionamiento offline o ante conectividad intermitente.
21. Alta inicial de cuentas y asignación de bodegas.
22. Migración de datos manuales.
23. Retención de movimientos e históricos.

## Actualizado por ADR-001

- 5: el jefe retira el acceso del empleado a su bodega; la cuenta y el historial de movimientos permanecen.
- 11: queda pendiente definir el lote del movimiento de ajuste generado por una edición directa de stock.
- 21: el alta de cuentas de empleado la realiza el jefe de la bodega en `operations-web`; el administrador de plataforma queda fuera de ese flujo en el MVP de esa app. **Cambio aprobado el 2026-11-26 (ADR-008):** para `admin-web` el administrador sí gestiona los cuatro roles, con autoprotección entre admins y baja lógica.
- Cuestión nueva: ¿cómo se representa una fila desactivada en las consultas y por cuánto tiempo se conserva?

## Actualizado por ADR-004

- 15: el usuario eligió Gemini gratuito. El proveedor quedó confirmado para el prototipo. El default pasó de `gemini-3.5-flash-lite` a `gemini-3.1-flash-lite` porque la prueba real devolvió `503 service_unavailable` por alta demanda del primero. Sigue pendiente de confirmación junto con la cuota real.
- 16: la justificación se limita a una frase sobre los campos disponibles (`stock`, `precio_venta`, `fecha_vencimiento`, `categoria`, `estado`). No se inventan costos, márgenes ni ventas.
- 18: si falta `GEMINI_API_KEY` o el proveedor falla, `POST /recommendations/generate` responde `503`; la UI muestra el error y el inventario no se modifica.
- Actualización de versión: `v1` funcionó para recomendaciones de texto, pero rechazó imagen inline en REG-IA con `400`; el endpoint compartido pasó a `v1beta/interactions` (ADR-004/ADR-005).
- Alcance: el usuario confirmó incluir también **aumentos de precio** junto a descuentos, precios y reposición. Esto se registra como expansión de CU-08/RF-12 en la especificación `REC-IA`.
- Cuestión nueva: ¿se persistirán las decisiones de EN-08 y las promociones con vigencia, o bastará con el cambio de precio confirmado por el jefe?

## Actualizado por ADR-005

- El usuario aprobó la expansión de alcance para registro asistido por foto, código de barras y voz. La exclusión original de “registro por voz/fotografía” queda limitada a registro **automático sin revisión**.
- `Código` usa los dígitos procesados de la imagen y consulta directamente Open Food Facts; no existe catálogo local de EAN. Si el código no está en la base, se informa y el usuario completa manualmente.
- La cantidad la fija el usuario en `Código`; Open Food Facts no expone precio ni vencimiento en este corte, así que tampoco se proponen (RN-12, RN-13).
- **Cambio de decisión del usuario (2026-11-26):** en `Voz`, la fuente de precio, vencimiento y código es el **dictado transcrito**, no una estimación. Gemini debe transcribir los ocho campos definidos en RN-12/RF-27. Solo si el audio los dice explícitamente; la fecha se expresa como ISO `AAAA-MM-DD` y no se deduce vida útil. `Foto` y `Código` mantienen precio y vencimiento manuales. Ya no rige la redacción anterior que los declaraba manuales en los tres modos.
- **Cambio de decisión del usuario (2026-11-26):** el botón del medio de `Código` alterna entre capturar la imagen enfocada y volver a encender la cámara. Se mantiene «Subir imagen» y «Leer dígitos» como alternativas.
- **Cambio de decisión del usuario (2026-11-26):** el selector de Ícono se amplía con emojis y keywords, con paridad exacta entre frontend y backend.
- **Cambio de decisión del usuario (2026-11-26):** Categoría pasa a ser un selector expandible estilo Notion con «Agregar nueva categoría». El catálogo se persiste en la base (`Categoria`), se reutiliza sin distinguir mayúsculas/minúsculas y cada producto guarda una sola categoría por nombre (RN-14/RF-29). `CATEGORIAS` queda como fallback con las mismas nueve categorías del seed/UI. Es un detalle de implementación de EN-03, no una nueva entidad de negocio.
- **Cambio de decisión del usuario (2026-11-26):** `Foto`/`Voz` pueden elegir entre modelos autorizados por el backend. Se rechazó un campo de texto libre en el navegador para no permitir modelos de pago o inexistentes; `GET /ai/models` publica la allowlist y `POST /products/extract` valida el id (RF-34/RN-17). La clave sigue solo en el backend. Ante un `503` por alta demanda se eligió esperar y reintentar; el selector es una alternativa manual, no un reintento automático.
- Se descartó `google_search` de Gemini para `Código`: el plan gratuito no incluye *Search grounding* y la prueba real devolvió `429 too_many_requests`. El resto de los modos sigue usando Gemini gratuito.
- Las pruebas usan solo multimedia sintético o propio por el riesgo del tier gratuito.
- Cuestiones abiertas residuales:
  - ¿Cuál es la precisión real del dictado de `precio_venta`, `fecha_vencimiento` y dígitos del código en audio con ruido o acentos? Pendiente de validar con grabaciones reales; el usuario debe corregir siempre antes de guardar.
  - ¿Cuál es la cuota real para multimedia de Gemini y cuál de los modelos autorizados tiene mayor disponibilidad en el uso real? El selector no responde por precisión ni por disponibilidad.
  - ¿Debe verificarse automáticamente alguna fuente antes de mostrar datos dictados o de Open Food Facts? Hoy son borradores revisables; la transcripción no se contrasta con una base externa.
  - ¿Se migrará a Files API si crece el tamaño de archivos?
  - ¿Se auditarán en EN-08 los borradores aceptados? Queda fuera de este corte.

## Actualizado por ADR-006

- El usuario pidió una sección `Ventas` para jefe y empleado con el historial de compras de usuarios `cliente`, y confirmó que las tablas del `customer-web` de su compañero son la referencia de coherencia.
- Se siembran tres compras demo sintéticas y se descuenta stock en la misma transacción; no se usan datos reales de clientes ni se integra una pasarela externa en este corte.
- Cuestiones abiertas nuevas:
  - ¿Cómo se registrará el responsable y el lote exigidos por RN-03/CU-05 cuando se integre el checkout real con `Movimiento`/`DetalleMovimiento`?
  - ¿Debe el cliente autenticarse en este backend con `/customer/auth/*` o en un servicio propio de `customer-web`? Hoy solo existe `POST /sales` para personal de operaciones.
  - ¿Se conservarán `pendiente`, `expirado`, `rechazado` y `pago_en_revision` en algún panel operativo, aunque no cuenten como ventas ni hayan descontado stock?
  - ¿Qué política de privacidad aplica al nombre del comprador mostrado en `Ventas`? Hoy se muestra `nombres apellidos`, sin correo ni teléfono.

## Actualizado por ADR-007

- La autenticación del comprador ya está resuelta en este backend con `/customer/auth/register|login|me` y token `rol = 'cliente'`; no se creó un servicio de identidad separado.
- Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` se muestran en `Mis pedidos` del comprador, pero siguen sin aparecer en `Ventas` porque no descontaron inventario. No se añadió un panel operativo para ellos.
- Los pagos quedan en modo académico: `LOCAL_SIMULATION` o Mercado Pago de prueba con verificación server-side. No hay cobro real ni pasarela de producción.
- Cuestiones abiertas nuevas:
  - ¿Se publicará `customer-web` en un dominio propio y con `CORS_ORIGINS` de producción? Hoy solo está previsto en `127.0.0.1:5174`.
  - ¿Qué cuenta de Mercado Pago de prueba y qué URL de webhook se usarán en un entorno compartido? Requiere credenciales de prueba reales.
  - ¿Se incorporará algún panel operativo para revisar `pago_en_revision`? La decisión actual es dejarlo visible solo al comprador y resolverlo manualmente.
  - ¿Debe el seed de demostración publicar ofertas también en `Bodega San Martín` sin sobrescribir inventario existente? Hoy solo crea ofertas en las bodegas nuevas que agrega.

## Actualizado por ADR-008

- El usuario aprobó que `admin-web` gestione los cuatro roles, incluidos jefes y empleados; ADR-001 se mantiene para `operations-web`.
- Precisó que una cuenta admin no puede borrar ni modificar cuentas de otros admins. Se implementó como `403` en el backend y botones deshabilitados en la UI; la propia cuenta puede editarse, pero no desactivarse.
- La baja es lógica para conservar historial. No se agregó borrado físico ni cambio de rol sobre cuentas existentes.
- Cuestiones abiertas nuevas:
  - ¿Se publicará `admin-web` en un dominio propio? El README anterior mencionaba `admin.bodesmart.com`, pero no hay decisión de despliegue confirmada.
  - ¿Se requiere cambio de contraseña del propio admin con verificación de contraseña actual? No se implementó en este corte.
  - ¿Se auditarán las altas y ediciones de cuentas realizadas por admin? Hoy solo se registra `ultimo_acceso`.
