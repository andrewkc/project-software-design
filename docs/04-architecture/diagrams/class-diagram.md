# Diagrama de clases del negocio

```mermaid
classDiagram
    direction TB
    class CuentaUsuario["Cuenta de usuario"] {
        idCuenta
        nombre
        correo
        rol
        estado
    }
    class Bodega {
        idBodega
        nombre
        direccion
        ubicacion
        presupuestoReposicion
    }
    class Producto {
        idProducto
        nombre
        categoria
        unidadMedida
        precioVenta
        estado
    }
    class MovimientoInventario["Movimiento de inventario"] {
        idMovimiento
        fechaHora
        tipo
        motivo
        total [0..1]
    }
    class DetalleMovimiento["Detalle de movimiento"] {
        idDetalle
        cantidad
        importeUnitario [0..1]
        subtotal [0..1]
    }
    class Lote {
        idLote
        fechaIngreso
        fechaVencimiento [0..1]
        cantidadDisponible
        costoUnitario
    }
    class Promocion {
        idPromocion
        precioPromocional
        fechaInicio
        fechaFin
        estado
    }
    class SugerenciaIA["Sugerencia de IA"] {
        idSugerencia
        fechaGeneracion
        tipo
        cantidadSugerida [0..1]
        precioSugerido [0..1]
        justificacion
        estadoDecision
        fechaDecision [0..1]
        cantidadAprobada [0..1]
        precioAprobado [0..1]
    }

    CuentaUsuario "0..1" -- "0..1" Bodega : agrupa personal
    CuentaUsuario "1" -- "0..1" Bodega : dirige
    CuentaUsuario "0..1" -- "0..*" Promocion : aprueba
    CuentaUsuario "0..*" -- "0..*" SugerenciaIA : revisa
    CuentaUsuario "1" -- "0..*" MovimientoInventario : realiza
    Bodega "1" -- "0..*" Producto : administra
    Bodega "1" -- "0..*" MovimientoInventario : registra
    Producto "1" -- "0..*" Promocion : tiene
    Producto "1" -- "0..*" SugerenciaIA : recibe
    Producto "1" -- "0..*" Lote : tiene
    MovimientoInventario "1" *-- "1..*" DetalleMovimiento : contiene
    Lote "1" -- "0..*" DetalleMovimiento : corresponde a
```

Se conservan las multiplicidades del README autocontenido. El diagrama es conceptual; no define tablas, claves foráneas, tipos SQL ni tecnología. La narrativa y las multiplicidades de personal/cuentas requieren reconciliación antes del diseño físico.
