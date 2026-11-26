# BodeSmart

<p align="center">
  <img src="apps/operations-web/src/assets/BodeSmart-Logo.png" alt="Logo de BodeSmart" width="320">
</p>

BodeSmart es una propuesta de aplicación para bodegas y minimarkets de barrio. Busca reemplazar el control de existencias en papel, tickets y memoria por registros sencillos y consultables.

El trabajo se apoya en entrevistas exploratorias. Esas entrevistas describen el problema, pero no demuestran que la herramienta reduzca pérdidas ni que sus recomendaciones sean acertadas. Esta documentación describe un MVP propuesto, no un producto terminado.

## El problema

Las bodegas entrevistadas no saben con certeza qué stock tienen. Los ingresos se anotan en cuadernos o documentos, las salidas se recuerdan o se apoyan en tickets, y los vencimientos se revisan de forma informal. Cuando aparece un problema, cuesta saber quién registró cada movimiento.

## Lo que propone BodeSmart

- Registrar entradas de mercadería ya recibida y salidas por venta o merma.
- Consultar inventario, existencias por lote y fechas de vencimiento.
- Identificar al responsable de cada movimiento.
- Supervisar el trabajo del personal desde una sola vista.
- Definir precios y promociones de uso interno.
- Recibir sugerencias de reposición, descuentos y aumentos de precio, siempre sujetas a la decisión del jefe.

La IA apoya la decisión. Nunca aprueba promociones, genera compras ni modifica el inventario por su cuenta.

## Quiénes lo usan

**Jefe de bodega.** Ve y administra toda su bodega. Puede bloquear filas, desactivar productos sin borrar el historial, fijar precios y aprobar promociones o sugerencias.

**Empleado.** Trabaja solo en la bodega asignada. Registra entradas y salidas, edita únicamente las filas que creó y no puede eliminarlas ni desactivarlas.

**Administrador interno.** Usa `admin-web` para gestionar cuentas de admin, jefe, empleado y cliente, y consultar bodegas. No puede editar ni desactivar cuentas de otros administradores. El panel no consulta costos ni ventas (ADR-008); sigue pendiente de validación real.

**Comprador.** Usa `customer-web` para ver ofertas, armar una cesta y reservar productos por diez minutos. El backend aprueba el pago de prueba y solo entonces descuenta stock; el historial del comprador muestra todos los estados, mientras `Ventas` muestra solo las compras pagadas.

## Las aplicaciones

| App | Dominio | Estado |
| --- | --- | --- |
| operations-web | app.bodesmart.com | Prototipo actual para jefe y empleado |
| admin-web | Local `127.0.0.1:5175` | Prototipo del panel de cuentas y bodegas con identidad de `operations-web`; sin dominio público confirmado (ADMIN-01/ADR-008) |
| customer-web | Local `127.0.0.1:5174` | Prototipo del MVP ampliado: catálogo, cesta, pedidos y pago de prueba (ADR-007); sin dominio público configurado |
| backend | No expuesto públicamente | Auth, perfiles, productos, categorías, registro asistido, recomendaciones, ventas, `/customer/*` y `/admin/*`; movimientos/lotes pendientes |
| database | No expuesto públicamente | Esquema y seed aplicados por Docker; sin app dedicada |

El prototipo de operations-web consumes una API HTTP con PostgreSQL: registra productos (también con asistencia de Gemini desde foto, código de barras o voz), muestra el inventario con ID por fila, permite bloquear y desactivar, crea empleados con contraseña generada, incluye una sección de recomendaciones IA solo para el jefe y una sección `Ventas` para jefe y empleado con el historial de compras pagadas de los clientes. Las reglas de roles, propiedad y bloqueo están registradas como decisiones propuestas y aplicadas al prototipo. No son requisitos aprobados para producción.

## Despliegue con Docker Compose

`docker-compose.yml` levanta `database`, `backend`, `operations-web`, `customer-web` y `admin-web`. El dominio `app.bodesmart.online` corresponde a **operations-web**. `admin-web` se publica en `http://127.0.0.1:5175` con API base local configurable por `VITE_API_BASE_URL`; `customer-web` en `http://127.0.0.1:5174` (ADR-007), sin dominio público configurado ni cobro real.

El compose define `build` e `image` para cada servicio: sirve para construir en local y para bajar las imágenes ya publicadas en el EC2. Las diferencias entre ambos entornos van en `.env` (ignorado por Git). Copiar `.env.example` a `.env` y completar los valores reales. Para la sección IA se necesita además `GEMINI_API_KEY` en el backend; `GEMINI_MODEL` tiene un default derivado de la documentación de Gemini, pero debe confirmarse con el modelo disponible en la cuenta; `GEMINI_ALLOWED_MODELS` es opcional y alimenta el selector de `Foto`/`Voz` sin sacar la clave del backend. Sin clave, el inventario sigue funcionando; los endpoints de recomendaciones y de registro asistido responden `503`.

Si quedaron contenedores creados manualmente, sacarlos una sola vez:

```bash
docker rm -f database backend operations-web customer-web admin-web
```

### En local

```powershell
Copy-Item .env.example .env
# en .env, usar el bloque "Local con Vite, sin nginx": comentar
# VITE_API_BASE_URL=https://api.bodesmart.online y poner VITE_API_BASE_URL=http://localhost:8000
docker compose down -v
docker compose up -d --build
```

Queda en `http://127.0.0.1:5173` y la API en `http://127.0.0.1:8000/health`.

### Publicar imágenes

Después de probar en local, **volver a dejar `.env` con el bloque EC2** (`FRONTEND_DOCKERFILE=Dockerfile` y `VITE_API_BASE_URL=https://api.bodesmart.online`) y reconstruir el frontend: la URL de la API se hornea en el build de Vite, así que un build local publicado dejaría el sitio apuntando a `localhost:8000`.

```powershell
docker compose config --quiet
docker compose config | Select-String "dockerfile:|VITE_API_BASE_URL|image:"
docker compose build
docker compose push
```

Para publicar solo lo que cambió: `docker compose build operations-web` y `docker compose push operations-web` (o `backend` / `database`).

### En el EC2

```bash
docker compose pull
docker compose down -v
docker compose up -d
```

El nginx del host no cambia: `app.bodesmart.online` sigue haciendo proxy a `127.0.0.1:3002` y `api.bodesmart.online` a `127.0.0.1:8000`.

### Volumen de la base

`docker compose down -v` borra el volumen `bodesmart-db` y `up` crea uno nuevo, así que `seed.sql` se ejecuta desde cero. Eso elimina jefes, empleados y productos creados. Después del seed hay que registrar el jefe desde la pantalla de registro con el nombre de bodega exacto `Bodega San Martín` para conservar los 26 productos sembrados.

Para ver logs: `docker compose logs -f backend`. Para el estado: `docker compose ps`.

## Recomendaciones IA

La sección de recomendaciones es jefe-only. El backend consulta Gemini con `store: false`, sanea la respuesta y devuelve sugerencias de descuento, aumento y reposición como referencia. La IA no aprueba cambios, no genera compras ni modifica inventario: al revisar un precio se abre el formulario y solo se guarda si el jefe confirma. La reposición aprobada tampoco cambia stock.

Solo se envían campos existentes: `nombre`, `categoria`, `stock`, `precio_venta`, `fecha_vencimiento` y `estado`. No se usan costos, márgenes ni ventas porque no están disponibles. La integración es un prototipo pendiente de validación con una clave real; las entrevistas son exploratorias y no demuestran reducción de pérdidas ni acierto de las sugerencias. Ver [ADR-004](docs/04-architecture/decisions/ADR-004-gemini-recomendaciones-ia.md) y [REC-IA](docs/05-specifications/recomendaciones-ia/spec.md).

## Registro asistido con Gemini

`Foto` y `Voz` envían multimedia al backend, que llama a Gemini con `store: false` y devuelve un borrador saneado. `Foto` propone nombre, ícono, categoría, cantidad (stock inicial) y unidad; `Voz` transcribe todos los campos dictados, también `precio_venta`, `fecha_vencimiento` y `codigo_barras` si se dicen. Precio y fecha se transcriben solo si se dicen explícitamente (fecha ISO `AAAA-MM-DD`), sin estimar vida útil. `Código` valida la imagen, consulta Open Food Facts con los dígitos procesados y propone nombre, ícono, categoría, unidad y fuente; no propone cantidad, precio ni vencimiento, que siguen manuales. Su botón del medio alterna entre usar la foto enfocada y volver a encender la cámara; «Subir imagen» y «Leer dígitos» siguen disponibles. Si el código no está en la base, se informa y se registra manualmente. El selector de Ícono ofrece 124 emojis con keywords y el de Categoría es expandible: permite «Agregar nueva categoría», persiste el catálogo en la base y guarda una sola categoría por producto. Todo se puede corregir antes de guardar: la asistencia no crea productos, movimientos ni cambios de stock; crear una categoría persiste solo ese catálogo. Las pruebas usan solo multimedia sintético o propio por el riesgo del tier gratuito y están pendientes de ejecución y validación real. Ver [ADR-005](docs/04-architecture/decisions/ADR-005-registro-asistido-por-ia.md) y [REG-IA](docs/05-specifications/registro-asistido-ia/spec.md).

## Ventas

`Ventas` aparece para **Jefe** y **Empleado** y muestra solo `Compra.estado = 'pagado'` de la bodega del token. Cada registro trae cliente, fecha de pago, total y líneas con producto, cantidad, precio unitario y subtotal congelados al momento de la compra. El backend descuenta el stock en la misma transacción en que guarda la compra: por eso una línea que diga «4 kg de manzana roja» implica que antes había al menos 4 kg y que el saldo ya bajó. Los estados `pendiente`, `expirado`, `rechazado` y `pago_en_revision` no se muestran porque no descontaron inventario.

El esquema toma como referencia las tablas del `customer-web` que implementó el compañero en `C:\projects-4\project-software-design`: `Oferta`, `Compra`, `DetalleCompra`, `Pago` y `ReservaCompra`, con idempotencia y reservas. El backend siembra tres compras sintéticas para la demostración y expone `POST /sales` como contrato transaccional. Con la ampliación ADR-007, `customer-web` ya consume `/customer/*` y comparte con `POST /sales` la misma regla de descuento atómico; no hay pasarela de cobro real. Ver [ADR-006](docs/04-architecture/decisions/ADR-006-ventas-historial-compra-atomica.md), [ADR-007](docs/04-architecture/decisions/ADR-007-cliente-web-pago-prueba.md) y [VENTAS-01](docs/05-specifications/ventas-historial/spec.md).

## Tienda de clientes

`customer-web` usa la misma paleta, escala tipográfica, menú y tarjeta de perfil que `operations-web`, con rol `Cliente`. El catálogo y los pedidos salen de la base del repositorio: `/customer/offers` publica solo ofertas vigentes con stock disponible descontando reservas activas, y `/customer/orders` muestra todos los estados del comprador. Para crear datos de prueba sin tocar los datos reales, ejecutar el seed opcional con `BODESMART_DEMO_SEED=1 python apps/backend/seed_customer_demo.py`; las credenciales del comprador demo quedan en `.demo-credentials.json` (ignorado por Git). La cuenta `cliente.demo@bodesmart.local` con contraseña `DemoCliente2026!` pertenece a las compras sintéticas del backend.

El pago de prueba puede ser local (`Simular pago`) o iniciarse en Mercado Pago de prueba. En ambos casos el navegador solo inicia o consulta: el backend verifica importe, referencia, moneda, cuenta y firma del webhook antes de aprobar. `ALLOW_SIMULATED_PAYMENT=false` desactiva la simulación local; las claves `MERCADOPAGO_ACCESS_TOKEN` y `MERCADOPAGO_WEBHOOK_SECRET` se leen desde `.env` y nunca se hornean en el frontend. Ver [ADR-007](docs/04-architecture/decisions/ADR-007-cliente-web-pago-prueba.md).

## Panel administrativo

`admin-web` usa la misma paleta, tipografía, menú y tarjeta de perfil que `operations-web`, con rol `Admin`. Gestiona cuentas de **admin, jefe, empleado y cliente** y consulta bodegas; no consulta costos, ventas ni precios. La baja es una desactivación lógica para conservar historial. Un administrador puede editar su propia cuenta, pero no desactivarla, y no puede editar ni desactivar a otro administrador.

Para la demo local, la cuenta sembrada es `admin@bodesmart.local` / `Admin123456`; es una credencial de prototipo hasheada por el backend en el arranque, no una credencial de producción. El panel usa el token separado `bodesmart-admin-token` y endpoints aislados `/admin/*`, sin tocar los contratos de jefe, empleado ni cliente. Ver [ADR-008](docs/04-architecture/decisions/ADR-008-admin-web-alcance-cuentas.md) y [ADMIN-01](docs/05-specifications/admin-web/spec.md).

## Lo que queda fuera del MVP

No se incluyen proveedores, integración con pasarelas de pago reales, facturación electrónica, entregas, contabilidad ni estimación de vida útil por IA. La interfaz de comprador y los pagos de prueba sí están incluidos en el MVP ampliado (ADR-007). `Pago.metodo_pago = 'LOCAL_SIMULATION'` y `MERCADOPAGO_TEST` son solo trazas de demostración académica, no cobros reales. El registro **automático** sin revisión sigue fuera del MVP: la asistencia aprobada en ADR-005 siempre requiere confirmación del usuario.

## Cómo se construye la documentación

Trabajamos por funcionalidad con el ciclo Descubrir, Especificar, Revisar, Planear, Tareas, Implementar, Validar y Aprender. Cada funcionalidad mantiene trazabilidad entre casos de uso, requisitos, reglas de negocio, entidades, pruebas y código.

Las afirmaciones se etiquetan como confirmadas, derivadas, propuestas o pendientes. Ante una contradicción, se registra como pregunta abierta o decisión de arquitectura. No se decide en silencio.

## Estado de certeza

- Confirmado: lo que dicen las entrevistas y la fuente original.
- Propuesto: reglas de roles, propiedad y bloqueo, y persistencia de perfiles en SQLite. Aplicadas solo al prototipo.
- Confirmado para el prototipo: proveedor Gemini, alcance de recomendaciones con descuentos, aumentos y reposición, expansión de alcance para registro asistido por foto, código y voz (ADR-005), incluidas las decisiones posteriores de transcripción de voz completa sin estimar vencimiento, botón de cámara alterno, emojis amplios con paridad, catálogo persistente de categorías y selector de modelo Gemini con allowlist; y alcance de `admin-web` sobre los cuatro roles con autoprotección entre administradores (ADR-008).
- Derivado/pendiente: modelo definitivo y cuota real de Gemini; precisión real del dictado de precio/fecha/dígitos; ejecución de `pytest`/`npm run build`; arquitectura de producción, despliegue final, métricas no funcionales y varias preguntas de negocio todavía abiertas.
