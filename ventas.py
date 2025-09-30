from clientes import crear_cliente_si_no_existe

# Función: Consultar orden de venta por nombre
def consultar_orden_de_venta(models, db, uid, password):
    orden = input("🧾 Ingresá el nombre de la orden de venta (ej. S00003): ")
    sale_orders = models.execute_kw(
        db, uid, password,
        'sale.order', 'search_read',
        [[['name', '=', orden]]],
        {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state'], 'limit': 1}
    )

    if not sale_orders:
        print("❌ No se encontró la orden de venta.")
        return

    sale = sale_orders[0]
    order_id = sale['id']
    print("\n🧾 Orden de venta encontrada:")
    print("Número:", sale['name'])
    print("Cliente:", sale['partner_id'][1])
    print("Total:", sale['amount_total'])
    print("Estado:", sale['state'])

    # Buscar líneas de venta
    sale_lines = models.execute_kw(
        db, uid, password,
        'sale.order.line', 'search_read',
        [[['order_id', '=', order_id]]],
        {'fields': ['product_id', 'product_uom_qty', 'price_unit', 'name']}
    )

    print("\n📦 Detalle de productos vendidos:")
    for line in sale_lines:
        product_id = line['product_id'][0]
        product_data = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_id],
            {'fields': ['x_studio_sku']}
        )
        sku = product_data[0].get('x_studio_sku', 'N/A')

        print("Producto:", line['product_id'][1])
        print("SKU:", sku)
        print("Cantidad:", line['product_uom_qty'])
        print("Precio unitario:", line['price_unit'])
        print("Descripción:", line['name'])
        print("-----")

# Función: Crear una orden de venta con dos productos
def crear_orden_de_venta(models, db, uid, password):
    cliente = input("👤 Ingresá el nombre del cliente: ")
    partner_id = crear_cliente_si_no_existe(models, db, uid, password, cliente)

    # Crear la orden de venta
    order_id = models.execute_kw(
        db, uid, password,
        'sale.order', 'create',
        [{
            'partner_id': partner_id,
            'date_order': '2025-09-29',
        }]
    )

    print(f"\n🛒 Orden creada con ID: {order_id}")

    # Ingresar dos SKUs
    for i in range(1, 3):
        sku = input(f"🔢 Ingresá el SKU del producto {i}: ")
        product_ids = models.execute_kw(
            db, uid, password,
            'product.product', 'search',
            [[['x_studio_sku', '=', sku]]],
            {'limit': 1}
        )

        if not product_ids:
            print(f"❌ Producto {i} no encontrado.")
            continue

        cantidad = float(input(f"📦 Cantidad del producto {i}: "))
        precio = float(input(f"💲 Precio unitario del producto {i}: "))

        # Crear línea de venta
        models.execute_kw(
            db, uid, password,
            'sale.order.line', 'create',
            [{
                'order_id': order_id,
                'product_id': product_ids[0],
                'product_uom_qty': cantidad,
                'price_unit': precio,
                'name': f"Producto {i} - SKU {sku}",
            }]
        )

    # Confirmar la orden para que impacte en el stock
    models.execute_kw(
        db, uid, password,
        'sale.order', 'action_confirm',
        [[order_id]]
    )

    print("✅ Orden confirmada y stock actualizado.")
