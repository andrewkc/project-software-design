# DESSOF · demo local de bodegas

Fases 1 a 3: base de datos, cuentas, tres tiendas de muestra, 12 productos, 15 lotes, gestión real de bodega y compra local simulada. Entra en **Gestión de bodega** para gestionar inventario y en **Comprar en bodegas** para ver ofertas, armar una cesta, reservar y simular un pago. La pantalla original sigue siendo un prototipo visual separado. La subfase 4.1 genera datos sintéticos calibrados con FreshRetailNet, la 4.2 entrena un modelo experimental y la 4.3 ofrece recomendaciones de precio con aprobación del dueño. Mercado Pago y Gemini quedan para las últimas subfases.

## Estructura

```text
backend/       Django: modelos, servicios transaccionales, API y pruebas
frontend/      React/Vite, panel de gestión y panel de comprador
compose.yaml   PostgreSQL 16 local
```

## Iniciar en PowerShell

Requisitos: Python 3.12 o versión compatible con Django 5.2, Node.js, npm y Docker Desktop. Desde esta carpeta:

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

## Comprobación

```powershell
python -m pytest -q
python backend\manage.py check
cd frontend
npm test
npm run build
```

Las pruebas de Python usan PostgreSQL real, no SQLite. Para una base distinta, configura `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` y `POSTGRES_PORT`. Los secretos y dependencias locales están ignorados por Git.

La API expone sesión y registro de compradores (`/api/v1/auth/*`), tiendas, ofertas públicas (`/api/v1/offers`), pedidos (`/api/v1/orders`), pago **simulado local** (`/api/v1/orders/{id}/simulate-payment`) y asistente local de solo lectura (`/api/v1/chat`). Las rutas `/api/v1/store/*` permiten gestionar inventario y ofertas. Solo el dueño puede ingresar stock, ajustar y modificar ofertas; el empleado registra ventas y consulta sin ver costos. Login y demás escrituras requieren CSRF; los datos de sesión se mantienen en cookie HttpOnly. Pedidos y movimientos usan claves de idempotencia y bloqueos de PostgreSQL. Un pedido reserva por hasta 10 minutos; una aprobación local consume la reserva y descuenta inventario una sola vez; rechazo o vencimiento la libera. La aprobación simulada no prueba la integración con Mercado Pago.

Los documentos de alcance y arquitectura están un nivel arriba, en los dos archivos `definicion de proyecto DESSOF - *.md`.

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
