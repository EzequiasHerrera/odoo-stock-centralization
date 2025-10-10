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