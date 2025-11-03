from datetime import datetime

def buscar_producto_por_sku(models, db, uid, password, sku):
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[['default_code', '=', sku]]],
        {'limit': 1}
    )

    if not product_ids:
        return None

    product = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [product_ids],
        {'fields': ['name', 'x_studio_color', 'x_studio_talle', 'qty_available', 'virtual_available', 'bom_count', 'product_tmpl_id']}
    )[0]

    resultado = {
        "sku": sku,
        "name": product['name'],
        "color": product.get('x_studio_color', 'N/A'),
        "talle": product.get('x_studio_talle', 'N/A'),
        "stock_disponible": product['qty_available'],
        "stock_virtual": product['virtual_available'],
        "bom": []
    }

    if product['bom_count'] > 0:
        bom_ids = models.execute_kw(
            db, uid, password,
            'mrp.bom', 'search',
            [[['product_id', '=', product_ids[0]]]],
            {'limit': 1}
        )

        if not bom_ids:
            tmpl_id = product['product_tmpl_id'][0]
            bom_ids = models.execute_kw(
                db, uid, password,
                'mrp.bom', 'search',
                [[['product_tmpl_id', '=', tmpl_id]]],
                {'limit': 1}
            )

        if bom_ids:
            bom_data = models.execute_kw(
                db, uid, password,
                'mrp.bom', 'read',
                [bom_ids],
                {'fields': ['type', 'bom_line_ids']}
            )[0]

            bom_lines = models.execute_kw(
                db, uid, password,
                'mrp.bom.line', 'read',
                [bom_data['bom_line_ids']],
                {'fields': ['product_id', 'product_qty']}
            )

            for line in bom_lines:
                comp_id = line['product_id'][0]
                comp_name = line['product_id'][1]
                comp_qty = line['product_qty']

                comp_data = models.execute_kw(
                    db, uid, password,
                    'product.product', 'read',
                    [comp_id],
                    {'fields': ['default_code', 'qty_available', 'virtual_available']}
                )[0]

                resultado["bom"].append({
                    "nombre": comp_name,
                    "sku": comp_data.get('default_code', 'N/A'),
                    "cantidad_en_kit": comp_qty,
                    "stock_disponible": comp_data['qty_available'],
                    "stock_virtual": comp_data['virtual_available']
                })

    return resultado

#   Consulta de AJUSTES DE INVENTARIO
def buscar_ajustes_inventario(models, db, uid, password):
    """
    Consulta los registros de stock.quant modificados hoy y muestra SKU, cantidad, stock virtual y fecha/hora.
    """
    # Fecha actual en formato ISO (sin zona horaria)
    hoy = datetime.today().strftime('%Y-%m-%dT00:00:00')

    # Buscar quants modificados hoy
    quants = models.execute_kw(db, uid, password,
        'stock.quant', 'search_read',
        [[['write_date', '>=', hoy]]],
        {'fields': ['product_id', 'quantity', 'write_date'], 'limit': 100}
    )

    for q in quants:
        product_id = q['product_id'][0] if q['product_id'] else None
        product_name = q['product_id'][1] if q['product_id'] else 'Sin nombre'
        cantidad = q['quantity']
        fecha_hora = q['write_date']  # Ya incluye fecha y hora en formato ISO

        # Consultar SKU y stock virtual desde product.product
        if product_id:
            producto = models.execute_kw(db, uid, password,
                'product.product', 'read',
                [product_id],
                {'fields': ['default_code', 'virtual_available']}
            )[0]

            sku = producto.get('default_code', 'Sin SKU')
            stock_virtual = producto.get('virtual_available', 'Desconocido')

            print(f"Producto: {product_name}")
            print(f"SKU: {sku}")
            print(f"Cantidad física: {cantidad}")
            print(f"Stock virtual: {stock_virtual}")
            print(f"Última modificación: {fecha_hora}")
            print("------")

    return quants


def actualizar_stock_odoo_por_sku(models, db, uid, password, sku, nueva_cantidad):
    
    """
    Actualiza el stock de un producto en Odoo usando el modelo stock.quant.
    """
    # Buscar el producto por SKU
    product_ids = models.execute_kw(db, uid, password,
        'product.product', 'search',
        [[['default_code', '=', sku]]], {'limit': 1})
    
    if not product_ids:
        raise ValueError(f"No se encontró producto con SKU '{sku}'")

    product_id = product_ids[0]

    # Buscar ubicación interna
    location_ids = models.execute_kw(db, uid, password,
        'stock.location', 'search',
        [[['usage', '=', 'internal']]], {'limit': 1})
    
    if not location_ids:
        raise ValueError("No se encontró ubicación interna")

    location_id = location_ids[0]

    # Buscar el stock.quant correspondiente
    quant_ids = models.execute_kw(db, uid, password,
        'stock.quant', 'search',
        [[
            ['product_id', '=', product_id],
            ['location_id', '=', location_id]
        ]], {'limit': 1})

    if quant_ids:
        # Actualizar cantidad existente
        models.execute_kw(db, uid, password,
            'stock.quant', 'write',
            [quant_ids, {'quantity': nueva_cantidad}])
    else:
        # Crear nuevo registro de stock.quant si no existe
        models.execute_kw(db, uid, password,
            'stock.quant', 'create',
            [{
                'product_id': product_id,
                'location_id': location_id,
                'quantity': nueva_cantidad
            }])

    return f"Stock actualizado para SKU '{sku}' a {nueva_cantidad} unidades."


#   Consultar SKU Pendientes por Ajuste de inventario
def buscar_sku_pendientes(models, db, uid, password):
    try:
        # Buscar registros con estado "Pendiente"
        ids = models.execute_kw(db, uid, password,
            'x_stock', 'search',
            [[['x_studio_estado', '=', 'Pendiente']]])

        if not ids:
            print("📭 No hay registros pendientes.")
            return

        # Leer los SKUs
        records = models.execute_kw(db, uid, password,
            'x_stock', 'read',
            [ids], {'fields': ['x_studio_sku']})

        for record in records:
            sku = record.get('x_studio_sku')
            record_id = record.get('id')
            print(f"🔍 SKU pendiente: {sku} (ID: {record_id})")

            try:
                # Intentar marcar como Procesado
                models.execute_kw(db, uid, password,
                    'x_stock', 'write',
                    [[record_id], {'x_studio_estado': 'Procesado'}])

                print(f"✅ Registro {record_id} marcado como 'Procesado'")
            except Exception as e:
                print(f"💥 Error al marcar registro {record_id}: {e}")

    except Exception as e:
        print(f"💥 Error general en buscar_sku_pendientes: {e}")
