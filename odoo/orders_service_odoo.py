#Adaptamos las funciones para que no necesiten inputs sino que se puedan invocar con parametros y sean funcionales
from clients_service_odoo import obtener_id_cliente_por_documento

#CREAR una orden de venta con tres productos a un cliente segun DOCUMENTO
def crear_orden_de_venta(models, db, uid, password, partner_id, fecha):
    order_id = models.execute_kw(
        db, uid, password,
        'sale.order', 'create',
        [{
            'partner_id': partner_id,
            'date_order': fecha,
        }]
    )
    print(f"\n🛒 Orden creada con ID: {order_id}")
    return order_id
#CONFIRMAR una orden con ORDER_ID
def confirmar_orden(models, db, uid, password, order_id):
    models.execute_kw(
        db, uid, password,
        'sale.order', 'action_confirm',
        [[order_id]]
    )
    print("✅ Orden confirmada y stock actualizado.")
#CONSULTAR orden de venta por NOMBRE
def consultar_orden_de_venta(models, db, uid, password, orden):
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

#Obtener SKUs y STOCK usando NOMBRE de orden de venta
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
            {'fields': ['default_code', 'virtual_available', 'product_tmpl_id']}
        )
        if product_data:
            sku = product_data[0].get('default_code', 'N/A')
            stock = product_data[0].get('virtual_available', 0.0)
            productos_actualizados.append({
                'default_code': sku,
                'virtual_available': stock
            })

            # Buscar BoM por product_id
            bom_ids = models.execute_kw(
                db, uid, password,
                'mrp.bom', 'search_read',
                [[['product_id', '=', product_id]]],
                {'fields': ['id', 'type'], 'limit': 1}
            )

            # Si no hay BoM por product_id, buscar por product_tmpl_id
            if not bom_ids:
                tmpl_id = product_data[0]['product_tmpl_id'][0]
                bom_ids = models.execute_kw(
                    db, uid, password,
                    'mrp.bom', 'search_read',
                    [[['product_tmpl_id', '=', tmpl_id]]],
                    {'fields': ['id', 'type'], 'limit': 1}
                )

            # Si hay BoM, agregar componentes
            if bom_ids and bom_ids[0]['type'] in ['phantom', 'normal']:
                bom_id = bom_ids[0]['id']
                bom_lines = models.execute_kw(
                    db, uid, password,
                    'mrp.bom.line', 'search_read',
                    [[['bom_id', '=', bom_id]]],
                    {'fields': ['product_id']}
                )
                for bom_line in bom_lines:
                    componente_id = bom_line['product_id'][0]
                    comp_data = models.execute_kw(
                        db, uid, password,
                        'product.product', 'read',
                        [componente_id],
                        {'fields': ['default_code', 'virtual_available']}
                    )[0]
                    productos_actualizados.append({
                        'default_code': comp_data.get('default_code', 'N/A'),
                        'virtual_available': comp_data.get('virtual_available', 0.0)
                    })

    # Procesar cada línea de venta
    for line in sale_lines:
        product_id = line['product_id'][0]
        agregar_producto(product_id)

    return productos_actualizados

# Función: Listar todas las listas de materiales (BoM) con su SKU
# OBJETIVO: mostrar los kits definidos en Odoo y sus códigos internos
def listar_boms_con_sku_y_componentes(models, db, uid, password):
    print("🔍 Buscando todas las listas de materiales (BoM)...")

    # Buscar todas las BoM
    todas_las_boms = models.execute_kw(
        db, uid, password,
        'mrp.bom', 'search_read',
        [[]],
        {'fields': ['id', 'product_id', 'product_tmpl_id', 'type']}
    )

    print(f"📦 Se encontraron {len(todas_las_boms)} listas de materiales.")

    resultado = []

    for bom in todas_las_boms:
        bom_id = bom['id']
        bom_type = bom['type']
        product_ref = bom.get('product_id')
        tmpl_ref = bom.get('product_tmpl_id')

        print(f"\n🔧 Procesando BoM ID {bom_id} | Tipo: {bom_type}")

        # Obtener datos del kit
        if product_ref:
            product_id = product_ref[0]
            product_data = models.execute_kw(
                db, uid, password,
                'product.product', 'read',
                [product_id],
                {'fields': ['name', 'default_code']}
            )
        elif tmpl_ref:
            tmpl_id = tmpl_ref[0]
            variant_ids = models.execute_kw(
                db, uid, password,
                'product.product', 'search_read',
                [[['product_tmpl_id', '=', tmpl_id]]],
                {'fields': ['name', 'default_code'], 'limit': 1}
            )
            product_data = variant_ids
        else:
            print("   ⚠️ Esta BoM no tiene producto ni plantilla asociada.")
            continue

        if not product_data:
            print("   ⚠️ No se pudo leer el producto asociado.")
            continue

        kit_info = product_data[0]
        kit_name = kit_info['name']
        kit_sku = kit_info.get('default_code', 'N/A')
        print(f"   ➤ Kit: {kit_name} | SKU: {kit_sku}")

        # Leer componentes de la BoM
        bom_lines = models.execute_kw(
            db, uid, password,
            'mrp.bom.line', 'search_read',
            [[['bom_id', '=', bom_id]]],
            {'fields': ['product_id', 'product_qty']}
        )

        componentes = []

        for line in bom_lines:
            comp_id = line['product_id'][0]
            comp_qty = line['product_qty']

            comp_data = models.execute_kw(
                db, uid, password,
                'product.product', 'read',
                [comp_id],
                {'fields': ['name', 'default_code']}
            )[0]

            comp_name = comp_data['name']
            comp_sku = comp_data.get('default_code', 'N/A')

            print(f"      - Componente: {comp_name} | SKU: {comp_sku} | Cantidad: {comp_qty}")

            componentes.append({
                'nombre': comp_name,
                'sku': comp_sku,
                'cantidad': comp_qty
            })

        resultado.append({
            'bom_id': bom_id,
            'kit_name': kit_name,
            'kit_sku': kit_sku,
            'tipo_bom': bom_type,
            'componentes': componentes
        })

    print(f"\n✅ Total de kits listados: {len(resultado)}")
    return resultado

# Función: Buscar kits donde un SKU aparece como componente
# OBJETIVO: listar los SKUs de los kits que incluyen el SKU dado en su BoM
def buscar_kits_que_contienen_componente(models, db, uid, password, sku_componente):
    print(f"🔍 Buscando en qué kits está incluido el SKU '{sku_componente}'...")

    # Buscar el producto por SKU
    producto = models.execute_kw(
        db, uid, password,
        'product.product', 'search_read',
        [[['default_code', '=', sku_componente]]],
        {'fields': ['id'], 'limit': 1}
    )

    if not producto:
        print(f"❌ No se encontró ningún producto con SKU '{sku_componente}'.")
        return []

    componente_id = producto[0]['id']

    # Buscar todas las BoM
    todas_las_boms = models.execute_kw(
        db, uid, password,
        'mrp.bom', 'search_read',
        [[]],
        {'fields': ['id', 'product_id', 'product_tmpl_id', 'type']}
    )

    print(f"📦 Se encontraron {len(todas_las_boms)} listas de materiales.")

    kits_encontrados = []

    for bom in todas_las_boms:
        bom_id = bom['id']
        bom_type = bom['type']
        product_ref = bom.get('product_id')
        tmpl_ref = bom.get('product_tmpl_id')

        print(f"\n🔧 Revisando BoM ID {bom_id} | Tipo: {bom_type}")

        # Leer líneas de componentes
        bom_lines = models.execute_kw(
            db, uid, password,
            'mrp.bom.line', 'search_read',
            [[['bom_id', '=', bom_id]]],
            {'fields': ['product_id']}
        )

        contiene_componente = any(line['product_id'][0] == componente_id for line in bom_lines)

        if contiene_componente:
            # Obtener SKU del kit
            if product_ref:
                kit_id = product_ref[0]
                kit_data = models.execute_kw(
                    db, uid, password,
                    'product.product', 'read',
                    [kit_id],
                    {'fields': ['default_code']}
                )[0]
                kit_sku = kit_data.get('default_code', 'N/A')
            elif tmpl_ref:
                tmpl_id = tmpl_ref[0]
                variant_data = models.execute_kw(
                    db, uid, password,
                    'product.product', 'search_read',
                    [[['product_tmpl_id', '=', tmpl_id]]],
                    {'fields': ['default_code'], 'limit': 1}
                )
                kit_sku = variant_data[0].get('default_code', 'N/A') if variant_data else 'N/A'
            else:
                kit_sku = 'N/A'

            print(f"   ➤ El componente está en el kit con SKU: {kit_sku}")
            kits_encontrados.append(kit_sku)

    print(f"\n✅ Total de kits que contienen el SKU '{sku_componente}': {len(kits_encontrados)}")
    return kits_encontrados

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

    for line in sale_lines:
        product_id = line['product_id'][0]

        # Leer el SKU y el stock disponible del producto
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

    return productos_actualizados