# odoo/precarga_boms.py
import logging
import sys

def precargar_boms(models, db, uid, password):
    """
    Precarga todas las BOMs desde Odoo en un diccionario invertido BOM_CACHE.
    Clave: SKU de componente
    Valor: lista de kits afectados con su SKU y stock disponible.
    """
    logging.info("📥 Precargando todas las BOMs desde Odoo...")

    # 1️⃣ Traer todas las BOMs
    todas_las_boms = models.execute_kw(
        db, uid, password,
        "mrp.bom", "search_read",
        [[]],
        {"fields": ["id", "product_id", "product_tmpl_id", "type"]}
    )
    logging.info(f"🔢 Total de BOMs encontradas: {len(todas_las_boms)}")

    # 2️⃣ Traer todas las líneas de BOMs
    todas_las_lineas = models.execute_kw(
        db, uid, password,
        "mrp.bom.line", "search_read",
        [[]],
        {"fields": ["bom_id", "product_id"]}
    )
    logging.info(f"🔢 Total de líneas de BOMs encontradas: {len(todas_las_lineas)}")

    # 3️⃣ Traer todos los productos
    todos_los_productos = models.execute_kw(
        db, uid, password,
        "product.product", "search_read",
        [[]],
        {"fields": ["id", "default_code", "virtual_available", "product_tmpl_id"]}
    )
    logging.info(f"🔢 Total de productos encontrados: {len(todos_los_productos)}")

    # Diccionarios auxiliares
    productos_por_id = {p["id"]: p for p in todos_los_productos}
    lineas_por_bom = {}
    for linea in todas_las_lineas:
        bom_id = linea["bom_id"][0]
        lineas_por_bom.setdefault(bom_id, []).append(linea)

    BOM_CACHE = {}

    # Construir BOM_CACHE
    for bom in todas_las_boms:
        bom_id = bom["id"]
        product_ref = bom.get("product_id")
        tmpl_ref = bom.get("product_tmpl_id")

        kit_id = None
        if product_ref:
            kit_id = product_ref[0]
        elif tmpl_ref:
            for p in todos_los_productos:
                if p["product_tmpl_id"][0] == tmpl_ref[0]:
                    kit_id = p["id"]
                    break

        if not kit_id or kit_id not in productos_por_id:
            continue

        kit_info = {
            "default_code": productos_por_id[kit_id]["default_code"],
            "virtual_available": productos_por_id[kit_id]["virtual_available"]
        }

        bom_lines = lineas_por_bom.get(bom_id, [])
        for line in bom_lines:
            comp_id = line["product_id"][0]
            comp_data = productos_por_id.get(comp_id)
            if not comp_data:
                continue
            sku_componente = comp_data["default_code"]
            BOM_CACHE.setdefault(sku_componente, []).append(kit_info)

    logging.info(f"✅ Precarga completa. BOMs procesadas: {len(todas_las_boms)}")
    logging.info(f"📦 Componentes indexados en BOM_CACHE: {len(BOM_CACHE)}")

    memoria_bytes = sys.getsizeof(BOM_CACHE)
    memoria_mb = memoria_bytes / (1024 * 1024)
    logging.info(f"💾 Memoria RAM estimada para BOM_CACHE: {memoria_mb:.2f} MB")

    return BOM_CACHE
