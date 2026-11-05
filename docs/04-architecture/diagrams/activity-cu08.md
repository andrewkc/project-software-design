# Actividad CU-08 — Revisar y aprobar un descuento sugerido

```mermaid
flowchart TB
    subgraph JB["Jefe de bodega"]
        direction TB
        Inicio((●))
        A1["Consultar sugerencias de descuentos"]
        A2["Seleccionar una sugerencia"]
        D2{"¿Rechaza la sugerencia?"}
        D3{"¿Modifica el precio sugerido?"}
        A3["Ingresar precio propuesto"]
        A4["Conservar precio sugerido"]
        M1(( ))
        A5["Definir inicio y fin de la promoción"]
        D5{"¿Confirma la aprobación?"}
        M2(( ))
    end

    subgraph SIS["Sistema"]
        direction TB
        S1["Mostrar sugerencias pendientes"]
        D1{"¿Hay sugerencias pendientes?"}
        S2["Informar que no hay sugerencias"]
        Fin1((◉))
        S3["Mostrar producto, existencias,<br/>precio sugerido y justificación"]
        S4["Registrar rechazo y responsable"]
        Fin2((◉))
        S5["Validar precio de descuento,<br/>fechas y disponibilidad de<br/>productos aptos para la venta"]
        D4{"¿Condiciones válidas?"}
        S6["Mostrar resumen de la promoción"]
        S7["Informar errores sin guardar cambios"]
        Fin3((◉))
        S8["Registrar decisión, valores aprobados,<br/>fecha y jefe responsable"]
        S9["Guardar promoción aprobada<br/>para aplicarla en las ventas<br/>registradas durante su vigencia"]
        S10["Dejar sugerencia pendiente<br/>sin modificar precios"]
        Fin4((◉))
    end

    Inicio --> A1
    A1 --> S1
    S1 --> D1
    D1 -- No --> S2 --> Fin1
    D1 -- Sí --> A2
    A2 --> S3
    S3 --> D2
    D2 -- Sí --> S4 --> Fin2
    D2 -- No --> D3
    D3 -- Sí --> A3 --> M1
    D3 -- No --> A4 --> M1
    M1 --> A5
    A5 --> S5
    S5 --> D4
    D4 -- No --> S7 --> Fin3
    D4 -- Sí --> S6
    S6 --> D5
    D5 -- Sí --> S8 --> S9 --> M2
    D5 -- No --> S10 --> M2
    M2 --> Fin4
```

Representa la variante de CU-08 que usa una sugerencia IA para aprobar una promoción interna. Las promociones manuales siguen validaciones comerciales equivalentes.
