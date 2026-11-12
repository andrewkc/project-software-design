# Bodega Clara — prototipo frontend

Prototipo adaptable a escritorio y móvil para la gestión interna de una bodega. Incluye un flujo de creación de cuenta, panel principal, catálogo local de productos, alertas de vencimiento, hallazgos de entrevistas y cuatro maneras de iniciar el registro de mercadería.

## Ejecutar

Desde esta carpeta:

```bash
npm install
npm run dev
```

Para comprobar la compilación de producción:

```bash
npm run build
```

## Qué incluye

- Registro de usuario y nombre del negocio; la información de demostración se guarda en el almacenamiento local del navegador.
- Inventario de muestra, búsqueda de productos y alta de productos con cantidad, unidad, precio y vencimiento.
- Alertas calculadas a partir de las fechas ingresadas y propuestas demostrativas de descuento/stock que la persona puede revisar, ajustar o descartar.
- Flujos demostrativos de foto, voz, escritura y código de barras. El navegador permite elegir/tomar una foto; voz, escaneo, análisis de imágenes y predicciones de IA no están conectados a servicios reales. La propuesta de precio es ilustrativa (10 % menos que el precio de muestra) y no modifica precios ni promociones reales.
- Pantalla de hallazgos: control de memoria o papel, dificultad para registrar ventas, pérdidas por vencimiento y necesidad de identificar a la persona que hizo cada movimiento.
- Oportunidad para validar en futuras entrevistas: documentar productos vencidos/deteriorados y los reclamos de devolución al proveedor. La gestión de proveedores no está en el MVP descrito en el modelo de negocio.

El archivo `Entrevistas.csv` no se encontró entre los archivos disponibles en el espacio de trabajo. Los hallazgos mostrados se basan en la descripción de entrevistas incluida en `Modelo_Negocio.docx` y en el problema adicional de devoluciones indicado por el equipo; deben contrastarse con las respuestas originales.

Este prototipo no reemplaza un sistema de inventario de producción. No hay autenticación real, backend, procesamiento automático de entradas, registro de ventas/mermas ni historial de auditoría.
