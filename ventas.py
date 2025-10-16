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
            {'fields': ['default_code']}
        )
        sku = product_data[0].get('default_code', 'N/A')

        print("Producto:", line['product_id'][1])
        print("SKU:", sku)
        print("Cantidad:", line['product_uom_qty'])
        print("Precio unitario:", line['price_unit'])
        print("Descripción:", line['name'])
        print("-----")

# Función: Crear una orden de venta con dos productos
def crear_orden_de_venta(models, db, uid, password):
#    nombre = input("👤 Ingresá el Nombre del cliente: ")
    documento = input("👤 Ingresá el Documento del cliente: ")
    partner_id = crear_cliente_si_no_existe(models, db, uid, password, documento)

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
    for i in range(1, 4):
        sku = input(f"🔢 Ingresá el SKU del producto {i}: ")
        product_ids = models.execute_kw(
            db, uid, password,
            'product.product', 'search',
            [[['default_code', '=', sku]]],
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


# Función: Obtener SKUs y stock actual desde una orden de venta
#      OBJETIVO: generar una lista de SKU y stock virtual para actualizar stock de TN.


def obtener_skus_y_stock(models, db, uid, password, nombre_orden):
    # Buscar la orden de venta por nombre
    sale_orders = models.execute_kw(
        db, uid, password,
        'sale.order', 'search_read',
        [[['name', '=', nombre_orden]]],
        {'fields': ['id'], 'limit': 1}
    )

    if not sale_orders:
        print("❌ No se encontró la orden de venta.")
        return []

    order_id = sale_orders[0]['id']

    # Buscar líneas de venta asociadas
    sale_lines = models.execute_kw(
        db, uid, password,
        'sale.order.line', 'search_read',
        [[['order_id', '=', order_id]]],
        {'fields': ['product_id']}
    )

    productos_actualizados = []

    def agregar_producto(product_id):
        product_data = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_id],
            {'fields': ['default_code', 'virtual_available']}
        )
        if product_data:
            sku = product_data[0].get('default_code', 'N/A')
            stock = product_data[0].get('virtual_available', 0.0)
            productos_actualizados.append({
                'default_code': sku,
                'virtual_available': stock
            })

    for line in sale_lines:
        product_id = line['product_id'][0]
        agregar_producto(product_id)

        # Verificar si el producto es un kit (tipo phantom o tiene BoM)
        boms = models.execute_kw(
            db, uid, password,
            'mrp.bom', 'search_read',
            [[['product_id', '=', product_id]]],
            {'fields': ['id', 'type']}
        )

        for bom in boms:
            if bom['type'] in ['phantom', 'normal']:  # 'phantom' suele usarse para kits
                bom_id = bom['id']
                bom_lines = models.execute_kw(
                    db, uid, password,
                    'mrp.bom.line', 'search_read',
                    [[['bom_id', '=', bom_id]]],
                    {'fields': ['product_id']}
                )
                for bom_line in bom_lines:
                    componente_id = bom_line['product_id'][0]
                    agregar_producto(componente_id)

    return productos_actualizados

