# app.py
from flask import Flask, request, abort
import os
import hmac
import hashlib
import threading
import logging
import time
import queue
from dotenv import load_dotenv
from datetime import datetime

from integration.idempotencia import verificar_idempotencia

from tiendanube.orders_service_tn import extract_order_data, get_order_by_id
from tiendanube.products_service_tn import update_stock_by_sku

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

# 🔧 Carga de variables de entorno
load_dotenv()

APP_SECRET = os.getenv("TIENDANUBE_SECRET")
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")

# 🌐 Inicialización de Flask
app = Flask(__name__)

# 🔁 Cola de tareas y worker dedicado

#cola_de_tareas = queue.Queue()
order_id_actual = None  # Valor inicial que no dispara procesamiento

def worker_manual():
    global order_id_actual
    logging.info("🧵 Worker manual iniciado.")
    while True:
        logging.info("---- Worker manual evaluando order_id...")
        if order_id_actual:
            logging.info(f"🚀 Procesando orden {order_id_actual}")
            try:
                tarea_de_prueba(order_id_actual)
#                procesar_orden(order_id_actual)
            except Exception as e:
                logging.exception(f"💥 Error al procesar orden: {e}")
            order_id_actual = None
            logging.info("✅ order_id_actual reiniciado a None")
        time.sleep(30)  # Evita loop activo    

#def worker_de_tareas():
#    logging.info("🧵 Worker de tareas iniciado.")
#    while True:
#        logging.info("🕓 Esperando tarea en la cola...")
#        order_id_actual = cola_de_tareas.get()
#        logging.info("📥 Tarea recibida. Ejecutando...")
#        try:
#            procesar_orden(order_id_actual)
#        except Exception as e:
#            logging.exception(f"💥 Error en tarea encolada: {str(e)}")
#        cola_de_tareas.task_done()
#        time.sleep(30)

# 🔐 Verificación de firma HMAC para asegurar que el webhook proviene de TiendaNube
def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)

# 🔁 Procesamiento de orden en segundo plano
def procesar_orden(order_id):
    logging.info(f"🧵 Iniciando procesamiento de orden {order_id}.")

    if not verificar_idempotencia(order_id):
        logging.warning(f"⚠️ Orden {order_id} ya fue procesada previamente. Abortando.")
        return

    try:
        order = get_order_by_id(order_id)
        if not order:
            logging.error(f"❌ No se pudo obtener la orden {order_id}")
            return


        order_data = extract_order_data(order)
        logging.info(f"📦 Datos extraídos de la orden {order_id}: {order_data}")

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

# 🔁 Tarea periódica de ajustes de inventario
def ajuste_inventario():
    logging.info("🚀 Hilo de tarea periódica iniciado.")
    while True:
        try:
            logging.info("⏱ Ejecutando tarea periódica...")
            ajustes_inventario_pendientes()
        except Exception as e:
            logging.exception(f"💥 Error en tarea periódica: {str(e)}")
        time.sleep(60)

def tarea_de_prueba(order_id):
    logging.info(f"🧪 Tarea de prueba ejecutada con order_id={order_id}")

# Endpoint para el / en respuesta a Render
@app.route("/")
def index():
    return "Servicio activo", 200


# 🌐 Endpoint principal que recibe el webhook
@app.route("/webhook", methods=["POST"])
def webhook():
#    raw_data = request.get_data()
#    hmac_header = request.headers.get("x-linkedstore-hmac-sha256")

#    if not verify_signature(raw_data, hmac_header):
#        abort(401, "Firma inválida")

    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        logging.warning("❌ Webhook sin JSON válido.")
        return "Falta JSON", 400

    order_id = data.get("id")
    if not order_id:
        logging.warning("❌ No se encontró el ID de la orden en el webhook.")
        return "Falta ID", 400

    order_id_actual = order_id
#    threading.Thread(target=tarea_de_prueba, args=(order_id,), daemon=True).start()
#    threading.Thread(target=procesar_orden, args=(order_id,), daemon=True).start()

#    cola_de_tareas.put(order_id)
#    cola_de_tareas.put(lambda: procesar_orden(order_id))
#    cola_de_tareas.put(lambda: tarea_de_prueba(order_id))
    return "", 200

# 🛠️ Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# 🧵 Lanzamos el worker de tareas y la tarea periódica
#threading.Thread(target=worker_de_tareas, daemon=True).start()
#threading.Thread(target=ajuste_inventario, daemon=True).start()

# 🚀 Inicio del servidor Flask - Funcionamiento local
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
