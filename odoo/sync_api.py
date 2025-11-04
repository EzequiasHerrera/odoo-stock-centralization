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
        registros_pendientes_ids = models.execute_kw(db, uid, password,
            'x_stock', 'search',
            [[['x_studio_estado', '=', 'Pendiente']]])

        if not registros_pendientes_ids:
            logging.info("📭 No hay ajustes de inventario pendientes en x_stock.")
            return

        # Leer los SKUs
        registros_pendientes_data = models.execute_kw(db, uid, password,
            'x_stock', 'read',
            [registros_pendientes_ids], {'fields': ['x_studio_sku']})

        skus_detectados = []

        for registro in registros_pendientes_data:
            sku = registro.get('x_studio_sku')
            if not sku:
                continue

            skus_detectados.append(sku)

            # Marcar como procesado en el momento que se toma
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

        # Buscar kits afectados
        kits_relacionados = get_affected_kits_by_components(skus_detectados)

        # Armar lista dicts de SKUs simples con su respectivo virtual_available
        productos_actualizados = []
        for sku in skus_detectados:
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

                stock_virtual = producto_data[0].get('virtual_available', 0.0)
                productos_actualizados.append({
                    "default_code": sku,
                    "virtual_available": stock_virtual
                })

            except Exception as e:
                logging.exception(f"💥 Error al consultar stock para SKU {sku}")

        # Unificar listas y eliminar duplicados
        conjunto_total = productos_actualizados + kits_relacionados
        mapa_skus = {}
        for producto in conjunto_total:
            sku = producto.get("default_code", "N/A")
            if sku not in mapa_skus:
                mapa_skus[sku] = producto

        lista_final_actualizacion = list(mapa_skus.values())
        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_actualizacion]}")

        # Actualizar stock en TiendaNube
        for producto in lista_final_actualizacion:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)
            update_stock_by_sku(sku, stock)
            logging.info(f"🔄 Stock actualizado en TiendaNube: SKU={sku}, stock={stock}")

        del skus_detectados
        del productos_actualizados
        del kits_relacionados
        del conjunto_total
        del mapa_skus
        del lista_final_actualizacion

    except Exception as e:
        logging.exception("💥 Error actualizando stock por ajuste de inventario")
