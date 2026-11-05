# Actividad CU-05 — Registrar salidas

```mermaid
flowchart TB
    subgraph JE["Jefe o empleado"]
        direction TB
        Inicio((●))
        A1["Seleccionar motivo de salida"]
        A2["Seleccionar productos, lotes<br/>y cantidades"]
        D5{"¿Confirma el registro?"}
        M3(( ))
    end

    subgraph SIS["Sistema"]
        direction TB
        S1["Verificar cantidades positivas<br/>y existencias disponibles"]
        D1{"¿Datos válidos y stock suficiente?"}
        S2["Informar errores"]
        Fin1((◉))
        D2{"¿Salida por venta?"}
        S3["Verificar que los productos<br/>sean aptos para la venta"]
        D3{"¿Productos aptos?"}
        S4["Aplicar precios y promociones vigentes"]
        S5["Calcular subtotales y total"]
        S6["Informar que no pueden venderse"]
        Fin2((◉))
        S7["Identificar salida como merma<br/>por vencimiento o deterioro"]
        M1(( ))
        S8["Mostrar resumen de la salida"]
        S9["Revalidar disponibilidad y condiciones"]
        D4{"¿Se mantienen válidas?"}
        S10["Guardar movimiento y detalles,<br/>identificar al responsable y descontar<br/>existencias en una sola operación"]
        S11["Mostrar confirmación"]
        S12["Informar cambios y solicitar<br/>una nueva revisión"]
        M2(( ))
        S13["Cancelar sin modificar existencias"]
        Fin3((◉))
    end

    Inicio --> A1 --> A2
    A2 --> S1
    S1 --> D1
    D1 -- No --> S2 --> Fin1
    D1 -- Sí --> D2
    D2 -- Sí --> S3
    D2 -- No --> S7
    S3 --> D3
    D3 -- Sí --> S4 --> S5 --> M1
    D3 -- No --> S6 --> Fin2
    S7 --> M1
    M1 --> S8
    S8 --> D5
    D5 -- Sí --> S9
    D5 -- No --> S13
    S9 --> D4
    D4 -- Sí --> S10 --> S11 --> M2
    D4 -- No --> S12 --> M2
    M2 --> M3
    S13 --> M3
    M3 --> Fin3
```

El diagrama distingue venta y merma. La venta calcula total; la confirmación guarda movimiento, detalles, responsable y descuento de existencias. Cancelar o detectar error no produce salida parcial.
