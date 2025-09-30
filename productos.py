# Función: Buscar producto por SKU
def buscar_producto_por_sku(models, db, uid, password):
    sku = input("🔍 Ingresá el SKU del producto: ")
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[['x_studio_sku', '=', sku]]],
        {'limit': 1}
    )

    if product_ids:
        product = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_ids],
            {'fields': ['name', 'x_studio_color', 'x_studio_talle', 'qty_available', 'virtual_available', 'bom_count']}
        )
        print("\n📦 Producto encontrado:")
        print("Nombre:", product[0]['name'])
        print("Color:", product[0].get('x_studio_color', 'N/A'))
        print("Talle:", product[0].get('x_studio_talle', 'N/A'))
        print("Stock disponible:", product[0]['qty_available'])
        print("Stock virtual:", product[0]['virtual_available'])
        print("BoM Count:", product[0]['bom_count'])
    else:
        print("❌ Producto no encontrado.")
