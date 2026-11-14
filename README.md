# DESSOF · demo local de bodegas

La demo local incluye base de datos, cuentas, tres tiendas de muestra, 12 productos, 15 lotes, gestión de bodega y compras con Mercado Pago en su ambiente de prueba. Entra en **Gestión de bodega** para gestionar inventario y en **Comprar en bodegas** para ver ofertas, armar una cesta y pagar con una tarjeta de prueba. La pantalla original sigue siendo un prototipo visual separado. La subfase 4.1 genera datos sintéticos calibrados con FreshRetailNet, la 4.2 entrena un modelo experimental y la 4.3 ofrece recomendaciones de precio con aprobación del dueño. Mercado Pago Checkout Pro de prueba se integra en la fase 4; Gemini queda pendiente.

## Estructura

```text
backend/       Django: modelos, servicios transaccionales, API y pruebas
frontend/      React/Vite, panel de gestión y panel de comprador
compose.yaml   PostgreSQL 16 local
```

## Iniciar en PowerShell

Requisitos: Python compatible con Django 5.2, Node.js, npm y PostgreSQL. Para el arranque estándar se usa Docker Desktop; en este equipo también está disponible `start_demo_local.ps1` con PostgreSQL 18 ya instalado. Desde esta carpeta:

```powershell
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\manage.py migrate
$env:DESSOF_DEMO_PASSWORD = 'UnaClaveLocalDe12CaracteresOMas!'
python backend\manage.py seed_demo
python backend\manage.py runserver
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Vite envía `/api` a `http://127.0.0.1:8000`. Las cuentas demo usan direcciones `@demo.example` (`admin`, `dueno.1` a `dueno.3`, `empleado.1` a `empleado.3`, `cliente.1` y `cliente.2`) y la contraseña indicada solo en tu entorno local. Cambia esa clave si compartes la base. `seed_demo` solo funciona en una base sin tiendas y se niega a duplicar datos.

## Reabrir esta demo local

En este equipo se creó una base PostgreSQL aislada en `.local-postgres/`, ignorada por Git, que escucha solo en `127.0.0.1:55432` y no modifica el PostgreSQL ya instalado. Para volver a iniciar la base, Django y React después de reiniciar Windows, ejecuta desde la carpeta del proyecto:

```powershell
.\start_demo_local.ps1
```

Abre `http://127.0.0.1:5173/` y entra en **Comprar en bodegas**. La cuenta de comprador cargada es `cliente.1@demo.example`. La clave de esta base local está en la variable `DESSOF_DEMO_PASSWORD` del archivo `.env`, ignorado por Git. Esta base y sus cuentas son solo de demostración; no están en Git. El script usa las herramientas de PostgreSQL 18 ya instaladas en este equipo.

## Comprobación

```powershell
python -m pytest -q
python backend\manage.py check
cd frontend
npm test
npm run build
```

Las pruebas de Python usan PostgreSQL real, no SQLite. Para una base distinta, configura `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` y `POSTGRES_PORT`. Los secretos y dependencias locales están ignorados por Git.

La API expone sesión y registro de compradores (`/api/v1/auth/*`), tiendas, ofertas públicas (`/api/v1/offers`), pedidos (`/api/v1/orders`), pago local o Checkout Pro de prueba (`/api/v1/orders/{id}/checkout`, `/api/v1/orders/{id}/verify-payment`) y asistente local de solo lectura (`/api/v1/chat`). Las rutas `/api/v1/store/*` permiten gestionar inventario y ofertas. Solo el dueño puede ingresar stock, ajustar y modificar ofertas; el empleado registra ventas y consulta sin ver costos. Login y demás escrituras requieren CSRF; los datos de sesión se mantienen en cookie HttpOnly. Pedidos y movimientos usan claves de idempotencia y bloqueos de PostgreSQL. Un pedido reserva por hasta 10 minutos; una aprobación local consume la reserva y descuenta inventario una sola vez; rechazo o vencimiento la libera. La aprobación de Mercado Pago se verifica en el servidor con referencia, importe, moneda, cuenta y aplicación antes de descontar inventario. El origen local de React está autorizado para CSRF solo en desarrollo. Un pago acreditado tras vencer la reserva pasa a revisión sin descontar stock.

Los documentos de alcance y arquitectura están un nivel arriba, en los dos archivos `definicion de proyecto DESSOF - *.md`.

## Pago de prueba con Mercado Pago

Coloca únicamente el **Access Token del entorno Prueba** en `.env`, como `MERCADOPAGO_ACCESS_TOKEN=...`; el archivo está ignorado por Git. Reinicia Django después de editarlo. La Public Key no se usa con Checkout Pro. En **Comprar en bodegas**, crea un pedido y pulsa **Pagar con Mercado Pago**. La página de pago se abre en otra pestaña; usa la tarjeta de prueba indicada por el panel de Mercado Pago. Al volver a la aplicación, esta comprueba automáticamente el resultado, y también ofrece **Comprobar ahora** si se necesita. Si el navegador bloquea la nueva pestaña, aparece un enlace alternativo. Si recargas la aplicación durante el pago, el pedido pendiente se recupera. El backend consulta el estado de la order; solo `processed/accredited` con el total exacto descuenta stock. El retorno del navegador por sí solo no confirma la compra. La reserva dura hasta diez minutos; si el pago llega después, queda en revisión sin descontar stock. La demo local no usa webhooks públicos y no debe utilizar credenciales de producción ni tarjetas reales.

## Subfase 4.1: datos sintéticos y evaluación

Genera un conjunto reproducible de 180 días, 3 bodegas, 12 productos y dos lotes por producto en cada ciclo de 9 días. La demanda se genera **una vez por producto y día**; las ventas se reparten entre lotes por cierre más próximo. `latent_demand_steps` es una etiqueta sintética, mientras `observed_sales_steps` puede quedar truncada por falta de stock. Los parámetros ocultos del simulador solo aparecen en el manifiesto y no en las columnas de entrenamiento.

```powershell
.\.venv\Scripts\python.exe backend\manage.py generate_ml_demo --stress
```

El comando escribe `demand.csv`, `lots.csv`, `allocations.csv` y `manifest.json` para las semillas 42, 43 y 44 en `backend/media/ml_synthetic/`, una ruta ignorada por Git y separada de PostgreSQL. El manifiesto contiene hashes SHA-256, campos admitidos, cortes temporales 60/20/20, una bodega y un producto reservados para pruebas sin datos previos, MAE de una media histórica causal de 7 días y métricas simuladas de ingresos, margen, sobrantes, descuento y violaciones. Los lotes no se comparten entre cortes. El estado `SYNTHETIC_BASELINE_ONLY` indica que **todavía no hay modelo entrenado ni eficacia comercial validada**; las comparaciones de modelos y decisiones de precio corresponden a 4.2 y 4.3.

### Calibración con FreshRetailNet-50K

El perfil versionado `backend/core/freshretail_profile.json` se calculó con los 4,5 millones de registros del split `train` de [FreshRetailNet-50K](https://huggingface.co/datasets/Dingdong-Inc/FreshRetailNet-50K) (CC BY 4.0). El script `backend/core/calibrate_freshretail.py` reproduce el perfil desde `train.parquet` y guarda su SHA-256. El generador usa la frecuencia de descuentos y el cociente observado de ventas de fin de semana entre días laborables. La frecuencia real de días con faltante se guarda como referencia y se compara con la simulada; no se fuerza una igualdad.

```powershell
.\.venv\Scripts\python.exe backend\core\calibrate_freshretail.py train.parquet backend\core\freshretail_profile.json
.\.venv\Scripts\python.exe backend\manage.py generate_ml_demo --stress
```

FreshRetailNet no publica precio absoluto, costo, lote, vencimiento ni demanda sin censura. El script genera precios PEN, costos y vencimientos con reglas y semilla; no son observaciones reales. La relación precio-demanda y la reducción de demanda por proximidad al vencimiento siguen siendo supuestos simulados. El perfil real permite revisar plausibilidad, **no demuestra que un descuento cause más ventas**.

### Entrenamiento experimental de demanda

```powershell
.\.venv\Scripts\python.exe backend\manage.py train_ml_demo
```

El comando entrena `HistGradientBoostingRegressor` con pérdida Poisson en CPU, usando solo los días de entrenamiento de tiendas/productos conocidos. Usa tienda y categoría, pero omite el identificador de producto para generalizar mejor; las ventas anteriores conservan señal de cada producto. Deja la validación y la prueba temporal fuera del ajuste, evalúa además una tienda y un producto no vistos y repite la prueba con semillas 43 a 47. Compara MAE contra la media observada de 7 días y verifica que subir el precio no aumente la predicción. Guarda el modelo y su informe JSON con hash SHA-256 en `backend/media/ml_models/`, ignorado por Git. La carga comprueba el hash y la versión de scikit-learn; solo deben cargarse artefactos locales de confianza.

El estado permanece `EXPERIMENTAL`: este entrenamiento valida predicción de **demanda sintética**, pero no demuestra resultados con ventas reales.

### Recomendaciones de precio con revisión del dueño

```powershell
.\.venv\Scripts\python.exe backend\manage.py evaluate_ml_pricing
```

El evaluador compara mantener el precio, una regla sencilla por vencimiento y la recomendación del modelo en escenarios sintéticos independientes de lotes. Guarda el informe en `backend/media/ml_models/pricing-evaluation.json`. Reporta sobrantes **esperados** bajo la ecuación simulada, ingresos, margen, descuentos y violaciones. Es una evaluación de la demo, no una prueba causal con ventas reales.

El dueño puede abrir **Gestión de bodega → Recomendaciones de precio**, analizar ofertas y aprobar o rechazar cada propuesta. La API usa `/api/v1/store/analysis`, `/api/v1/store/recommendations` y `/api/v1/store/recommendations/{id}/decision`. Solo considera lotes activos con límite vigente y datos dentro del rango del modelo; si faltan días de historial, mantiene el precio. Los productos de categorías que el modelo no conoce también quedan en `KEEP`. El precio propuesto respeta costo, descuento máximo, piso y precio actual. Antes de aprobar se vuelven a comprobar versiones, stock, reservas, vigencia y límite; una propuesta vieja queda `STALE`. Todos los cambios aprobados tienen auditoría. Las recomendaciones requieren aprobación manual: el modo automático sigue deshabilitado mientras el modelo sea experimental.

Las bodegas ficticias recién cargadas no tienen ventas históricas, por lo que el análisis normal mantiene sus precios. En desarrollo, el dueño puede elegir **Analizar con historial simulado (solo demo)**. Esa opción usa otra semilla del generador y etiqueta cada recomendación como simulada; no agrega ventas a la base operativa. Solo está disponible con `DEBUG=1` para las tres bodegas demo. El dueño debe aprobar manualmente cualquier propuesta.
