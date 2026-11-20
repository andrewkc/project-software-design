def profile_out(row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "name": row["name"],
        "nombres": row["nombres"],
        "apellidos": row["apellidos"],
        "email": row["email"],
        "store": row["store"],
        "activo": bool(row["activo"]),
        "creadoEn": row["creado_en"],
        "revocadoEn": row["revocado_en"],
    }


def product_out(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "icon": row["icon"],
        "stock": row["stock"],
        "unit": row["unit"],
        "price": row["price"],
        "expires": row["expires"],
        "creadoPor": row["creado_por"],
        "bloqueado": bool(row["bloqueado"]),
        "bloqueadoPor": row["bloqueado_por"],
        "activo": bool(row["activo"]),
    }


def movement_out(row, details: list) -> dict:
    return {
        "id": row["id"],
        "fechaHora": row["fecha_hora"],
        "tipo": row["tipo"],
        "motivo": row["motivo"],
        "total": row["total"],
        "responsableId": row["responsable_id"],
        "responsableNombre": row["responsable_nombre"],
        "productoId": row["producto_id"],
        "stockAnterior": row["stock_anterior"],
        "stockNuevo": row["stock_nuevo"],
        "diferencia": row["diferencia"],
        "detalles": details,
    }
