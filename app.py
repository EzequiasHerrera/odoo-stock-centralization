# Esta va a ser la función principal que maneje los webhooks y actúe en consecuencia
from flask import Flask, request, abort
import os
import hmac
import hashlib
import threading  # 👈 Import necesario para ejecutar en segundo plano
import logging
import time

from integration.idempotencia import verificar_idempotencia

from dotenv import load_dotenv

from tiendanube.orders_service_tn import extract_order_data, get_order_by_id
from tiendanube.products_service_tn import update_stock_by_sku

from datetime import datetime

from odoo.products_service_odoo import get_affected_kits_by_components
from odoo.clients_service_odoo import get_client_id_by_dni
from odoo.sync_api import ajustes_inventario_pendientes
from odoo.orders_service_odoo import (
    create_sales_order,
    confirm_sales_order,
    cargar_producto_a_orden_de_venta,
    get_order_name_by_id,
    get_skus_and_stock_from_order
)

load_dotenv()

# OBTENGO DATOS DE TN
APP_SECRET = os.getenv("TIENDANUBE_SECRET")
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")

app = Flask(__name__)       #Se define el EndPoint para funcionamiento en Render

# 🔐 Verificación de firma HMAC para asegurar que el webhook proviene de TiendaNube
def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)

# 🔁 Función que procesa la orden en segundo plano
def procesar_orden(order_id):
    logging.info(f"🧵 Iniciando procesamiento de orden {order_id} en hilo secundario.")

    # 🔁 Verificación de idempotencia
    if not verificar_idempotencia(order_id):
        logging.warning(f"⚠️ Orden {order_id} ya fue procesada previamente. Abortando.")
        return

    try:
        # TIENDA NUBE
        order = get_order_by_id(order_id)
        if not order:
            logging.error(f"❌ No se pudo obtener la orden {order_id}")
            return

        order_data = extract_order_data(order)
        logging.info(f"📦 Datos extraídos de la orden {order_id}: {order_data}")

        # ODOO
        client_dni = order_data.get("client_data", {}).get("dni")
        client_name = order_data.get("client_data", {}).get("name")
        client_email = order_data.get("client_data", {}).get("email")

        client_id_odoo = get_client_id_by_dni(client_dni, client_name, client_email)
        date = datetime.now()
        order_sale_id_odoo = create_sales_order(client_id_odoo, date)
        logging.info(f"🧾 Orden de venta creada en Odoo: {order_sale_id_odoo}")

        for producto in order_data.get("products_data", []):
            sku = producto.get("sku")
            quantity = int(producto.get("quantity", 0))
            price = float(producto["price"]) if producto.get("price") else 0.0
            cargar_producto_a_orden_de_venta(order_sale_id_odoo, sku, quantity, price)
            logging.info(f"➕ Producto agregado: SKU={sku}, cantidad={quantity}, precio={price}")

        confirm_sales_order(order_sale_id_odoo)
        logging.info(f"✅ Orden de venta confirmada en Odoo: {order_sale_id_odoo}")

        order_name = get_order_name_by_id(order_sale_id_odoo)
        affected_products = get_skus_and_stock_from_order(order_name)
        skus_componentes = [p["default_code"] for p in affected_products]
        affected_kits = get_affected_kits_by_components(skus_componentes)

        final_sku_list = affected_products + affected_kits
        skus_unicos = {}
        for item in final_sku_list:
            sku = item.get("default_code", "N/A")
            if sku not in skus_unicos:
                skus_unicos[sku] = item

        lista_final_sin_duplicados = list(skus_unicos.values())
        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_sin_duplicados]}")

        for producto in lista_final_sin_duplicados:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)
            update_stock_by_sku(sku, stock)
            logging.info(f"🔄 Stock actualizado en TiendaNube: SKU={sku}, stock={stock}")

        logging.info(f"🎯 Orden {order_id} procesada exitosamente.")

    except Exception as e:
        logging.exception(f"💥 Error procesando la orden {order_id}: {str(e)}")

def ajuste_inventario():
    logging.info("🚀 Hilo de tarea periódica iniciado.")
    while True:
        try:
            logging.info("⏱ Ejecutando tarea periódica...")
            ajustes_inventario_pendientes()

        except Exception as e:
            logging.exception(f"💥 Error en tarea periódica: {str(e)}")
        time.sleep(60)  # Espera 5 minutos = 300


#"""         AGREGAR COMENTARIO PARA FUNCIONAMIENTO NORMAL
# 🌐 Endpoint principal que recibe el webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    hmac_header = request.headers.get("x-linkedstore-hmac-sha256")
    raw_data = request.get_data()

    # Verifico la firma del webhook
    if not verify_signature(raw_data, hmac_header):
        abort(401, "Firma inválida")

    # Extraigo el ID de la orden desde el JSON recibido
    data = request.json
    order_id = data.get("id")

    if not order_id:
        print("❌ No se encontró el ID de la orden en el webhook.")
        return "Falta ID", 400

    # ✅ Devuelvo OK inmediatamente para evitar reintentos de TiendaNube
    logging.info(f"📨 Webhook recibido con order_id={order_id}. Lanzando procesamiento en segundo plano.")
    threading.Thread(target=procesar_orden, args=(order_id,), daemon=True).start()
    logging.info("✅ Envío 200 OK a TiendaNube en respuesta al webhook.")
    return "OK", 200

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# 🧵 Lanzamos la tarea periódica en segundo plano - Ajuste de Inventario periódico
threading.Thread(target=ajuste_inventario, daemon=True).start()


# 🚀 Inicio del servidor Flask - Funcionamiento local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

#"""

"""        ELIMINAR ESTE COMENTARIO PARA EJECUCIÓN NORMAL
# ----------------------------------------------------------TESTING ----------------------------------------------------------
# 🔁 Lógica reutilizable
# 🧪 Testing manual sin Flask

def webhook_testing():
    ordenes_de_prueba = [
        "1816913106",
        "1816914094",
        "1816935101",
    ]

    logging.info("🧪 Iniciando test manual con órdenes de TiendaNube...")
    threads = []

    for order_id in ordenes_de_prueba:
        logging.info(f"🧪 Lanzando procesamiento para orden {order_id}")
        t = threading.Thread(target=procesar_orden, args=(order_id,))
        t.start()
        threads.append(t)

    # Esperar a que todos los hilos terminen
    for t in threads:
        t.join()

if __name__ == "__main__":
    webhook_testing()

"""
# ELIMINAR ESTE COMENTARIO PARA EJECUCION NORMAL