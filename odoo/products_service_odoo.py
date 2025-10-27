from odoo.connect_odoo import connect_odoo
import logging

def obtener_producto_por_sku(sku):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo conectar a Odoo para obtener producto.")
        return None

    try:
        product_id = models.execute_kw(
            db, uid, password,
            "product.product", "search",
            [[["default_code", "=", sku]]],
            {"limit": 1}
        )

        if not product_id:
            logging.warning(f"❌ No se encontró producto con SKU '{sku}'.")
            return None

        product = models.execute_kw(
            db, uid, password,
            "product.product", "read",
            [product_id],
            {
                "fields": [
                    "name", "x_studio_color", "x_studio_talle",
                    "qty_available", "virtual_available",
                    "bom_count", "product_tmpl_id"
                ]
            }
        )[0]

        resultado = {
            "sku": sku,
            "product_id": product_id[0],
            "name": product["name"],
            "color": product.get("x_studio_color", "N/A"),
            "talle": product.get("x_studio_talle", "N/A"),
            "stock_disponible": product["qty_available"],
            "stock_virtual": product["virtual_available"],
            "bom_count": product["bom_count"],
            "product_tmpl_id": product["product_tmpl_id"][0],
        }

        logging.info(f"📦 Producto obtenido: {resultado}")
        return resultado

    except Exception as e:
        logging.exception(f"💥 Error obteniendo producto por SKU '{sku}': {str(e)}")
        return None

def obtener_bom_producto_por_id(product_id, product_tmpl_id):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo conectar a Odoo para obtener BoM.")
        return []

    try:
        bom_ids = models.execute_kw(
            db, uid, password,
            "mrp.bom", "search",
            [[["product_id", "=", product_id]]],
            {"limit": 1}
        )

        if not bom_ids:
            bom_ids = models.execute_kw(
                db, uid, password,
                "mrp.bom", "search",
                [[["product_tmpl_id", "=", product_tmpl_id]]],
                {"limit": 1}
            )

        if not bom_ids:
            logging.warning(f"❌ No se encontró BoM para producto ID {product_id}.")
            return []

        bom_data = models.execute_kw(
            db, uid, password,
            "mrp.bom", "read",
            [bom_ids],
            {"fields": ["type", "bom_line_ids"]}
        )[0]

        bom_lines = models.execute_kw(
            db, uid, password,
            "mrp.bom.line", "read",
            [bom_data["bom_line_ids"]],
            {"fields": ["product_id", "product_qty"]}
        )

        bom = []
        for line in bom_lines:
            comp_id = line["product_id"][0]
            comp_name = line["product_id"][1]
            comp_qty = line["product_qty"]

            comp_data = models.execute_kw(
                db, uid, password,
                "product.product", "read",
                [comp_id],
                {"fields": ["default_code", "qty_available", "virtual_available"]}
            )[0]

            bom.append({
                "nombre": comp_name,
                "sku": comp_data.get("default_code", "N/A"),
                "cantidad_en_kit": comp_qty,
                "stock_disponible": comp_data["qty_available"],
                "stock_virtual": comp_data["virtual_available"]
            })

        logging.info(f"🔧 BoM obtenido para producto ID {product_id}: {bom}")
        return bom

    except Exception as e:
        logging.exception(f"💥 Error obteniendo BoM para producto ID {product_id}: {str(e)}")
        return []

def obtener_producto_con_bom_por_sku(sku):
    producto = obtener_producto_por_sku(sku)
    if not producto:
        return None

    if producto["bom_count"] > 0:
        bom = obtener_bom_producto_por_id(producto["product_id"], producto["product_tmpl_id"])
        producto["bom"] = bom
    else:
        producto["bom"] = []

    logging.info(f"📦 Producto con BoM: {producto}")
    return producto

def get_affected_kits_by_components(lista_skus_componentes):
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo conectar a Odoo para buscar kits afectados.")
        return []

    kits_actualizados = []

    try:
        for sku_componente in lista_skus_componentes:
            logging.info(f"🔍 Buscando kits que contienen el componente '{sku_componente}'...")

            producto = models.execute_kw(
                db, uid, password,
                "product.product", "search_read",
                [[["default_code", "=", sku_componente]]],
                {"fields": ["id"], "limit": 1}
            )

            if not producto:
                logging.warning(f"❌ No se encontró el producto con SKU '{sku_componente}'.")
                continue

            componente_id = producto[0]["id"]

            todas_las_boms = models.execute_kw(
                db, uid, password,
                "mrp.bom", "search_read",
                [[]],
                {"fields": ["id", "product_id", "product_tmpl_id", "type"]}
            )

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
                    elif tmpl_ref:
                        tmpl_id = tmpl_ref[0]
                        variant_data = models.execute_kw(
                            db, uid, password,
                            "product.product", "search_read",
                            [[["product_tmpl_id", "=", tmpl_id]]],
                            {"fields": ["id"], "limit": 1}
                        )
                        if not variant_data:
                            continue
                        kit_id = variant_data[0]["id"]
                    else:
                        continue

                    kit_data = models.execute_kw(
                        db, uid, password,
                        "product.product", "read",
                        [kit_id],
                        {"fields": ["default_code", "virtual_available"]}
                    )

                    if kit_data:
                        kits_actualizados.append({
                            "default_code": kit_data[0].get("default_code", "N/A"),
                            "virtual_available": kit_data[0].get("virtual_available", 0.0)
                        })

        logging.info(f"✅ Kits afectados encontrados: {kits_actualizados}")
        return kits_actualizados

    except Exception as e:
        logging.exception(f"💥 Error buscando kits afectados: {str(e)}")
        return []
