import logging

def create_sales_order(client_id, date, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para crear orden.")
        return None

    try:
        order_id = models.execute_kw(
            db, uid, password,
            "sale.order", "create",
            [{"partner_id": client_id,
              "date_order": date,
              "client_order_ref": 'TiendaNube'       # Identifico el Origen
            }]
        )
        logging.info(f"🛒 Orden creada con ID: {order_id}")
        return order_id
    except Exception as e:
        logging.exception(f"💥 Error creando orden de venta: {str(e)}")
        return None

def confirm_sales_order(order_id, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para confirmar orden.")
        return

    try:
        models.execute_kw(db, uid, password, "sale.order", "action_confirm", [[order_id]])
        logging.info(f"✅ Orden confirmada en Odoo: ID={order_id}")
    except Exception as e:
        logging.exception(f"💥 Error confirmando orden {order_id}: {str(e)}")

def get_order_name_by_id(order_id, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para obtener nombre de orden.")
        return None

    try:
        result = models.execute_kw(
            db, uid, password,
            "sale.order", "search_read",
            [[["id", "=", order_id]]],
            {"fields": ["name"], "limit": 1}
        )
        if result:
            name = result[0]["name"]
            logging.info(f"🔎 Nombre de orden {order_id}: {name}")
            return name
        else:
            logging.warning(f"❌ No se encontró la orden con ID {order_id}")
            return None
    except Exception as e:
        logging.exception(f"💥 Error obteniendo nombre de orden {order_id}: {str(e)}")
        return None

def get_skus_and_stock_from_order(order_name, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para obtener SKUs.")
        return []

    try:
        sale_orders = models.execute_kw(
            db, uid, password,
            "sale.order", "search_read",
            [[["name", "=", order_name]]],
            {"fields": ["id"], "limit": 1}
        )

        if not sale_orders:
            logging.warning(f"❌ No se encontró la orden de venta con nombre {order_name}")
            return []

        order_id = sale_orders[0]["id"]

        sale_lines = models.execute_kw(
            db, uid, password,
            "sale.order.line", "search_read",
            [[["order_id", "=", order_id]]],
            {"fields": ["product_id"]}
        )

        productos_actualizados = []

        def add_product(product_id):
            product_data = models.execute_kw(
                db, uid, password,
                "product.product", "read",
                [product_id],
                {"fields": ["default_code", "virtual_available", "product_tmpl_id"]}
            )
            if product_data:
                sku = product_data[0].get("default_code", "N/A")
                stock = product_data[0].get("virtual_available", 0.0)
                productos_actualizados.append({"default_code": sku, "virtual_available": stock})

                bom_ids = models.execute_kw(
                    db, uid, password,
                    "mrp.bom", "search_read",
                    [[["product_id", "=", product_id]]],
                    {"fields": ["id", "type"], "limit": 1}
                )

                if not bom_ids:
                    tmpl_id = product_data[0]["product_tmpl_id"][0]
                    bom_ids = models.execute_kw(
                        db, uid, password,
                        "mrp.bom", "search_read",
                        [[["product_tmpl_id", "=", tmpl_id]]],
                        {"fields": ["id", "type"], "limit": 1}
                    )

                if bom_ids and bom_ids[0]["type"] in ["phantom", "normal"]:
                    bom_id = bom_ids[0]["id"]
                    bom_lines = models.execute_kw(
                        db, uid, password,
                        "mrp.bom.line", "search_read",
                        [[["bom_id", "=", bom_id]]],
                        {"fields": ["product_id"]}
                    )
                    for bom_line in bom_lines:
                        componente_id = bom_line["product_id"][0]
                        comp_data = models.execute_kw(
                            db, uid, password,
                            "product.product", "read",
                            [componente_id],
                            {"fields": ["default_code", "virtual_available"]}
                        )[0]
                        productos_actualizados.append({
                            "default_code": comp_data.get("default_code", "N/A"),
                            "virtual_available": comp_data.get("virtual_available", 0.0)
                        })

        for line in sale_lines:
            product_id = line["product_id"][0]
            add_product(product_id)

        logging.info(f"📦 Productos actualizados desde orden {order_name}: {productos_actualizados}")
        return productos_actualizados

    except Exception as e:
        logging.exception(f"💥 Error obteniendo SKUs desde orden {order_name}: {str(e)}")
        return []

def consultar_orden_de_venta(orden, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para consultar orden.")
        return

    try:
        sale_orders = models.execute_kw(
            db, uid, password,
            "sale.order", "search_read",
            [[["name", "=", orden]]],
            {"fields": ["id", "name", "partner_id", "amount_total", "state"], "limit": 1}
        )

        if not sale_orders:
            logging.warning(f"❌ No se encontró la orden de venta con nombre {orden}")
            return

        sale = sale_orders[0]
        order_id = sale["id"]
        logging.info(f"🧾 Orden encontrada: {sale}")

        sale_lines = models.execute_kw(
            db, uid, password,
            "sale.order.line", "search_read",
            [[["order_id", "=", order_id]]],
            {"fields": ["product_id", "product_uom_qty", "price_unit", "name"]}
        )

        for line in sale_lines:
            product_id = line["product_id"][0]
            product_data = models.execute_kw(
                db, uid, password,
                "product.product", "read",
                [product_id],
                {"fields": ["default_code"]}
            )
            sku = product_data[0].get("default_code", "N/A")
            logging.info(f"🧾 Producto: {line['product_id'][1]}, SKU: {sku}, Cantidad: {line['product_uom_qty']}, Precio: {line['price_unit']}, Descripción: {line['name']}")

    except Exception as e:
        logging.exception(f"💥 Error consultando orden de venta {orden}: {str(e)}")

def cargar_producto_a_orden_de_venta(order_id, sku, cantidad, precio_unitario, models, db, uid, password):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para agregar producto.")
        return None

    try:
        product_ids = models.execute_kw(
            db, uid, password,
            "product.product", "search",
            [[["default_code", "=", sku]]],
            {"limit": 1}
        )

        if not product_ids:
            logging.warning(f"❌ Producto con SKU '{sku}' no encontrado.")
            return None

        product_id = product_ids[0]

        sale_line_id = models.execute_kw(
            db, uid, password,
            "sale.order.line", "create",
            [{
                "order_id": order_id,
                "product_id": product_id,
                "product_uom_qty": cantidad,
                "price_unit": precio_unitario,
                "name": f"Producto - SKU {sku}"
            }]
        )

        logging.info(f"✅ Producto '{sku}' agregado a orden {order_id} con línea ID: {sale_line_id}")
        return sale_line_id

    except Exception as e:
        logging.exception(f"💥 Error agregando producto '{sku}' a orden {order_id}: {str(e)}")
        return None
