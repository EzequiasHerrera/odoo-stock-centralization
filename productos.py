# Función: Buscar producto por SKU
def buscar_producto_por_sku(models, db, uid, password):
    sku = input("🔍 Ingresá el SKU del producto: ")

    # Buscar el producto por campo personalizado SKU
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
#        [[['x_studio_sku', '=', sku]]],
        [[['default_code', '=', sku]]],
        {'limit': 1}
    )

    if not product_ids:
        print("❌ Producto no encontrado.")
        return

    # Leer los datos del producto
    product = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [product_ids],
        {'fields': ['name', 'x_studio_color', 'x_studio_talle', 'qty_available', 'virtual_available', 'bom_count', 'product_tmpl_id']}
    )[0]

    print("\n📦 Producto encontrado:")
    print("Nombre:", product['name'])
    print("Color:", product.get('x_studio_color', 'N/A'))
    print("Talle:", product.get('x_studio_talle', 'N/A'))
    print("Stock disponible:", product['qty_available'])
    print("Stock virtual:", product['virtual_available'])
    print("BoM Count:", product['bom_count'])

    # Si el producto tiene una BoM, buscarla
    if product['bom_count'] > 0:
        print("🔧 Verificando si el producto tiene BoM...")

        # Intentar buscar BoM por variante
        bom_ids = models.execute_kw(
            db, uid, password,
            'mrp.bom', 'search',
            [[['product_id', '=', product_ids[0]]]],
            {'limit': 1}
        )

        # Si no se encuentra, buscar por plantilla
        if not bom_ids:
            tmpl_id = product['product_tmpl_id'][0]
            bom_ids = models.execute_kw(
                db, uid, password,
                'mrp.bom', 'search',
                [[['product_tmpl_id', '=', tmpl_id]]],
                {'limit': 1}
            )

        # Si se encontró una BoM, leerla
        if bom_ids:
            print("📋 BoM encontrada. Leyendo componentes...")
            bom_data = models.execute_kw(
                db, uid, password,
                'mrp.bom', 'read',
                [bom_ids],
                {'fields': ['type', 'bom_line_ids']}
            )[0]

            print("\n🧩 Este producto tiene una lista de materiales (BoM):")
            print("Tipo de BoM:", bom_data['type'])

            if bom_data['bom_line_ids']:
                print("Componentes:")
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

                    # Leer stock y SKU del componente
                    comp_data = models.execute_kw(
                        db, uid, password,
                        'product.product', 'read',
                        [comp_id],
                        {'fields': ['default_code', 'qty_available', 'virtual_available']}
                    )[0]

                    print("🧱 Componente:", comp_name)
                    print("SKU:", comp_data.get('default_code', 'N/A'))
                    print("Cantidad en kit:", comp_qty)
                    print("Stock disponible:", comp_data['qty_available'])
                    print("Stock virtual:", comp_data['virtual_available'])
                    print("-----")
        else:
            print("⚠️ El producto tiene BoM pero no se encontró ninguna asociada ni por variante ni por plantilla.")
