from odoo.connect_odoo import connect_odoo
import logging

def create_sales_order(client_id, date):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para crear orden.")
        return None

    try:
        order_id = models.execute_kw(
            db, uid, password,
            "sale.order", "create",
            [{"partner_id": client_id, "date_order": date}]
        )
        logging.info(f"🛒 Orden creada con ID: {order_id}")
        return order_id
    except Exception as e:
        logging.exception(f"💥 Error creando orden de venta: {str(e)}")
        return None

def confirm_sales_order(order_id):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para confirmar orden.")
        return

    try:
        models.execute_kw(db, uid, password, "sale.order", "action_confirm", [[order_id]])
        logging.info(f"✅ Orden confirmada en Odoo: ID={order_id}")
    except Exception as e:
        logging.exception(f"💥 Error confirmando orden {order_id}: {str(e)}")

def get_order_name_by_id(order_id):
    models, db, uid, password = connect_odoo()
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

def get_skus_and_stock_from_order(order_name):
    models, db, uid, password = connect_odoo()
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

def consultar_orden_de_venta(orden):
    models, db, uid, password = connect_odoo()
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

def cargar_producto_a_orden_de_venta(order_id, sku, cantidad, precio_unitario):
    models, db, uid, password = connect_odoo()
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

def listar_boms_con_sku_y_componentes():
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para listar BoMs.")
        return []

    try:
        logging.info("🔍 Buscando todas las listas de materiales (BoM)...")
        todas_las_boms = models.execute_kw(
            db, uid, password,
            "mrp.bom", "search_read",
            [[]],
            {"fields": ["id", "product_id", "product_tmpl_id", "type"]}
        )

        logging.info(f"📦 Se encontraron {len(todas_las_boms)} listas de materiales.")
        resultado = []

        for bom in todas_las_boms:
            bom_id = bom["id"]
            bom_type = bom["type"]
            product_ref = bom.get("product_id")
            tmpl_ref = bom.get("product_tmpl_id")

            kit_info = None
            if product_ref:
                product_id = product_ref[0]
                kit_info = models.execute_kw(
                    db, uid, password,
                    "product.product", "read",
                    [product_id],
                    {"fields": ["name", "default_code"]}
                )[0]
            elif tmpl_ref:
                tmpl_id = tmpl_ref[0]
                variant_ids = models.execute_kw(
                    db, uid, password,
                    "product.product", "search_read",
                    [[["product_tmpl_id", "=", tmpl_id]]],
                    {"fields": ["name", "default_code"], "limit": 1}
                )
                if variant_ids:
                    kit_info = variant_ids[0]

            if not kit_info:
                logging.warning(f"⚠️ BoM ID {bom_id} sin producto asociado.")
                continue

            kit_name = kit_info["name"]
            kit_sku = kit_info.get("default_code", "N/A")
            logging.info(f"🔧 Procesando BoM ID {bom_id} | Kit: {kit_name} | SKU: {kit_sku}")

            bom_lines = models.execute_kw(
                db, uid, password,
                "mrp.bom.line", "search_read",
                [[["bom_id", "=", bom_id]]],
                {"fields": ["product_id", "product_qty"]}
            )

            componentes = []
            for line in bom_lines:
                comp_id = line["product_id"][0]
                comp_qty = line["product_qty"]
                comp_data = models.execute_kw(
                    db, uid, password,
                    "product.product", "read",
                    [comp_id],
                    {"fields": ["name", "default_code"]}
                )[0]
                componentes.append({
                    "nombre": comp_data["name"],
                    "sku": comp_data.get("default_code", "N/A"),
                    "cantidad": comp_qty
                })

            resultado.append({
                "bom_id": bom_id,
                "kit_name": kit_name,
                "kit_sku": kit_sku,
                "tipo_bom": bom_type,
                "componentes": componentes
            })

        logging.info(f"✅ Total de kits listados: {len(resultado)}")
        return resultado

    except Exception as e:
        logging.exception(f"💥 Error listando BoMs: {str(e)}")
        return []

def buscar_kits_que_contienen_componente(sku_componente):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para buscar kits.")
        return []

    try:
        logging.info(f"🔍 Buscando en qué kits está incluido el SKU '{sku_componente}'...")
        producto = models.execute_kw(
            db, uid, password,
            "product.product", "search_read",
            [[["default_code", "=", sku_componente]]],
            {"fields": ["id"], "limit": 1}
        )

        if not producto:
            logging.warning(f"❌ No se encontró ningún producto con SKU '{sku_componente}'.")
            return []

        componente_id = producto[0]["id"]

        todas_las_boms = models.execute_kw(
            db, uid, password,
            "mrp.bom", "search_read",
            [[]],
            {"fields": ["id", "product_id", "product_tmpl_id", "type"]}
        )

        logging.info(f"📦 Se encontraron {len(todas_las_boms)} listas de materiales.")
        kits_encontrados = []

        for bom in todas_las_boms:
            bom_id = bom["id"]
            bom_type = bom["type"]
            product_ref = bom.get("product_id")
            tmpl_ref = bom.get("product_tmpl_id")

            bom_lines = models.execute_kw(
                db, uid, password,
                "mrp.bom.line", "search_read",
                [[["bom_id", "=", bom_id]]],
                {"fields": ["product_id"]}
            )

            contiene_componente = any(
                line["product_id"][0] == componente_id for line in bom_lines
            )

            if contiene_componente:
                if product_ref:
                    kit_id = product_ref[0]
                    kit_data = models.execute_kw(
                        db, uid, password,
                        "product.product", "read",
                        [kit_id],
                        {"fields": ["default_code"]}
                    )[0]
                    kit_sku = kit_data.get("default_code", "N/A")
                elif tmpl_ref:
                    tmpl_id = tmpl_ref[0]
                    variant_data = models.execute_kw(
                        db, uid, password,
                        "product.product", "search_read",
                        [[["product_tmpl_id", "=", tmpl_id]]],
                        {"fields": ["default_code"], "limit": 1}
                    )
                    kit_sku = variant_data[0].get("default_code", "N/A") if variant_data else "N/A"
                else:
                    kit_sku = "N/A"

                logging.info(f"➤ El componente está en el kit con SKU: {kit_sku}")
                kits_encontrados.append(kit_sku)

        logging.info(f"✅ Total de kits que contienen el SKU '{sku_componente}': {len(kits_encontrados)}")
        return kits_encontrados

    except Exception as e:
        logging.exception(f"💥 Error buscando kits que contienen el SKU '{sku_componente}': {str(e)}")
        return []
