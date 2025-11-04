import requests

from odoo.connect_odoo import connect_odoo
from odoo.products_service_odoo import get_affected_kits_by_components
from tiendanube.products_service_tn import update_stock_by_sku

import logging

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


def ajustes_inventario_pendientes():
    models, db, uid, password = connect_odoo()
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo conectar a Odoo para obtener Ajustes de Inventario de Sync API")
        return

    try:
        # Buscar registros con estado "Pendiente"
        ids = models.execute_kw(db, uid, password,
            'x_stock', 'search',
            [[['x_studio_estado', '=', 'Pendiente']]])

        if not ids:
            logging.info("📭 No hay ajustes de inventario pendientes en x_stock.")
            return

        # Leer los SKUs
        records = models.execute_kw(db, uid, password,
            'x_stock', 'read',
            [ids], {'fields': ['x_studio_sku']})

        lista_skus = []

        for record in records:
            sku = record.get('x_studio_sku')
            if not sku:
                continue

            lista_skus.append(sku)

            # Marcar como procesado en el momento que se toma
            record_id = record.get('id')
            try:
                activar_automatizacion_odoo(record_id)
                logging.info(f"✅ Registro x_stock {record_id} marcado como 'Procesado' para SKU {sku}")

            except Exception as e:
                logging.exception(f"💥 Falló la escritura del estado en el registro {record_id}")

        if not lista_skus:
            logging.info("📭 No se encontraron SKUs válidos para procesar.")
            return

        logging.info(f"📦 SKUs pendientes detectados: {lista_skus}")

        # Buscar kits afectados
        kits_afectados = get_affected_kits_by_components(lista_skus)

        # Armar lista dicts de SKUs simples con su respectivo virtual_available
        componentes_dict = []
        for sku in lista_skus:
            try:
                producto_ids = models.execute_kw(db, uid, password,
                    'product.product', 'search',
                    [[['default_code', '=', sku]]])

                if not producto_ids:
                    logging.warning(f"⚠️ No se encontró producto para SKU {sku}")
                    continue

                producto_data = models.execute_kw(db, uid, password,
                    'product.product', 'read',
                    [producto_ids], {'fields': ['virtual_available']})

                virtual_available = producto_data[0].get('virtual_available', 0.0)
                componentes_dict.append({
                    "default_code": sku,
                    "virtual_available": virtual_available
                })

            except Exception as e:
                logging.exception(f"💥 Error al consultar stock para SKU {sku}")

        # Unificar listas y eliminar duplicados
        final_sku_list = componentes_dict + kits_afectados
        skus_unicos = {}
        for item in final_sku_list:
            sku = item.get("default_code", "N/A")
            if sku not in skus_unicos:
                skus_unicos[sku] = item

        lista_final_sin_duplicados = list(skus_unicos.values())
        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_sin_duplicados]}")

        # Actualizar stock en TiendaNube
        for producto in lista_final_sin_duplicados:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)
            update_stock_by_sku(sku, stock)
            logging.info(f"🔄 Stock actualizado en TiendaNube: SKU={sku}, stock={stock}")

        del lista_skus
        del componentes_dict
        del kits_afectados
        del final_sku_list
        del skus_unicos
        del lista_final_sin_duplicados

    except Exception as e:
        logging.exception("💥 Error actualizando stock por ajuste de inventario")
