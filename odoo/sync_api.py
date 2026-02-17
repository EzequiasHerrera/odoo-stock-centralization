import requests
import logging

from tiendanube.products_service_tn import update_stock_by_sku
from odoo.products_service_odoo import get_affected_kits_by_components

def activar_automatizacion_odoo(record_id):
    url = "https://pintimates.odoo.com/web/hook/ba293fd7-ec47-435b-869f-93d2084222d5"
    payload = {
        "_model": "x_stock",
        "_id": record_id
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.info(f"✅ Automatización ejecutada para registro {record_id}")
        else:
            logging.error(f"💥 Error al ejecutar webhook: {response.status_code} - {response.text}")
    except Exception as e:
        logging.exception(f"💥 Excepción al enviar webhook: {e}")

def ajustes_inventario_pendientes(models, db, uid, password, BOM_CACHE):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo conectar a Odoo para obtener Ajustes de Inventario de Sync API")
        return

    try:
        registros_pendientes_ids = models.execute_kw(
            db, uid, password,
            'x_stock', 'search',
            [[['x_studio_estado', '=', 'Pendiente']]]
        )

        if not registros_pendientes_ids:
            logging.info("📭 No hay ajustes de inventario pendientes en x_stock.")
            return

        registros_pendientes_data = models.execute_kw(
            db, uid, password,
            'x_stock', 'read',
            [registros_pendientes_ids],
            {'fields': ['x_studio_sku']}
        )

        skus_detectados = []

        for registro in registros_pendientes_data:
            sku = registro.get('x_studio_sku')
            if not sku:
                continue

            skus_detectados.append(sku)

            registro_id = registro.get('id')
            try:
                activar_automatizacion_odoo(registro_id)
                logging.info(f"✅ Registro x_stock {registro_id} marcado como 'Procesado' para SKU {sku}")
            except Exception as e:
                logging.exception(f"💥 Falló la escritura del estado en el registro {registro_id}")

        if not skus_detectados:
            logging.info("📭 No se encontraron SKUs válidos para procesar.")
            return

        logging.info(f"📦 SKUs pendientes detectados: {skus_detectados}")

        # Usar BOM_CACHE en lugar de get_affected_kits_by_components
        kits_relacionados = []
        for sku in skus_detectados:
            kits_relacionados.extend(BOM_CACHE.get(sku, []))

        # Refrescar stock de los SKUs detectados directamente desde Odoo
        productos_actualizados = []
        for sku in skus_detectados:
            try:
                producto_ids = models.execute_kw(
                    db, uid, password,
                    'product.product', 'search',
                    [[['default_code', '=', sku]]]
                )

                if not producto_ids:
                    logging.warning(f"⚠️ No se encontró producto para SKU {sku}")
                    continue

                producto_data = models.execute_kw(
                    db, uid, password,
                    'product.product', 'search_read',
                    [[["id", "in", producto_ids]]],
                    {"fields": ["id", "default_code", "virtual_available"]}
                )

                if producto_data:
                    productos_actualizados.append(producto_data[0])

            except Exception as e:
                logging.exception(f"💥 Error al consultar stock para SKU {sku}")

        # Unir productos y kits
        conjunto_total = productos_actualizados + kits_relacionados
        mapa_skus = {}
        for producto in conjunto_total:
            sku = producto.get("default_code", "N/A")
            if sku not in mapa_skus:
                mapa_skus[sku] = producto

        lista_final_actualizacion = list(mapa_skus.values())

        # Refrescar stock de todos los SKUs finales desde Odoo
        product_ids = [item["id"] for item in lista_final_actualizacion if "id" in item]
        if product_ids:
            productos_actualizados = models.execute_kw(
                db, uid, password,
                "product.product", "search_read",
                [[("id", "in", product_ids)]],
                {"fields": ["id", "default_code", "virtual_available"]}
            )
            productos_por_id = {p["id"]: p for p in productos_actualizados}
            for item in lista_final_actualizacion:
                if "id" in item and item["id"] in productos_por_id:
                    item["virtual_available"] = productos_por_id[item["id"]]["virtual_available"]

        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_actualizacion]}")

        for producto in lista_final_actualizacion:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)

            # ⚠️ No actualizar SKUs de FunSales
            if "|" in sku:
                logging.info(f"⏭️ SKU {sku} afectado, omitido (FunSales). Stock actual: {stock}")
                continue

            update_stock_by_sku(sku, stock)
            logging.info(f"🔄 Stock actualizado en TiendaNube: SKU={sku}, stock={stock}")

        logging.info(f"🔄 Ajuste de Inventario pendiente terminado correctamente!")

    except Exception as e:
        logging.exception("💥 Error actualizando stock por ajuste de inventario")

def hay_skus_pendientes(models, db, uid, password):
    if not all([models, db, uid, password]):
        return False

    try:
        ids = models.execute_kw(db, uid, password,
            'x_stock', 'search',
            [[['x_studio_estado', '=', 'Pendiente']]])
        return bool(ids)
    except Exception as e:
        logging.exception("💥 Error verificando SKUs pendientes")
        return False
