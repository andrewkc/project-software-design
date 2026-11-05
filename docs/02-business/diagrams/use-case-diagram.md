# Diagrama de casos de uso

```mermaid
flowchart LR
    ADMIN["👤 Administrador de la app"]
    EMP["👤 Empleado de bodega"]
    JEFE["👤 Jefe de bodega"]

    subgraph SISTEMA["Gestión interna de bodegas"]
        direction TB
        CU01(["CU-01<br/>Administrar cuentas y accesos<br/>de la aplicación"])
        CU05(["CU-05<br/>Registrar salidas por venta,<br/>vencimiento o deterioro"])
        CU04(["CU-04<br/>Registrar entradas<br/>de mercadería"])
        CU06(["CU-06<br/>Consultar inventario y<br/>alertas de vencimiento"])
        CU02(["CU-02<br/>Gestionar los datos de la bodega<br/>y sus productos"])
        CU03(["CU-03<br/>Gestionar empleados<br/>de la bodega"])
        CU07(["CU-07<br/>Supervisar los registros<br/>de los empleados"])
        CU08(["CU-08<br/>Gestionar precios, descuentos<br/>y promociones"])
        CU09(["CU-09<br/>Revisar y aprobar sugerencias<br/>de reposición"])
    end

    ADMIN --- CU01
    EMP --- CU05
    EMP --- CU04
    EMP --- CU06
    JEFE --- CU02
    JEFE --- CU03
    JEFE --- CU07
    JEFE --- CU08
    JEFE --- CU09
    JEFE ---> EMP

    classDef actor fill:#ffffff,stroke:#333333,color:#000000
    classDef usecase fill:#eeeeee,stroke:#777777,color:#000000
    class ADMIN,EMP,JEFE actor
    class CU01,CU02,CU03,CU04,CU05,CU06,CU07,CU08,CU09 usecase
```

La fuente explica que la generalización del jefe hacia el empleado significa que el jefe puede realizar sus funciones. Flowchart es una aproximación visual, no notación UML estricta.
