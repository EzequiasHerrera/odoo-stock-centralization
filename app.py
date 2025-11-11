# app.py — Webhook + Worker con Redis para Render
from flask import Flask, request
import os
import hmac
import hashlib
import logging
import threading
import time
import redis
from datetime import datetime
from dotenv import load_dotenv

# --- Módulos propios ---
from integration.idempotencia import verificar_idempotencia
from tiendanube.orders_service_tn import extract_order_data, get_order_by_id
from tiendanube.products_service_tn import update_stock_by_sku
from odoo.connect_odoo import connect_odoo
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

# --- Cargar variables de entorno ---
load_dotenv()
APP_SECRET = os.getenv("TIENDANUBE_SECRET")
REDIS_URL = os.getenv("REDIS_URL")
QUEUE_KEY = "ordenes_pendientes"

# --- Inicializar Flask ---
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# --- Configuración global de logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- Conexión a Redis ---
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL no está definida")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# 🔐 Verificación de firma HMAC para asegurar que el webhook proviene de TiendaNube
def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)

# 🌐 Endpoint principal que recibe el webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        hmac_header = request.headers.get("x-linkedstore-hmac-sha256")
        raw_data = request.get_data()

        if not verify_signature(raw_data, hmac_header):
            return "", 401

        data = request.json
        order_id = data.get("id")
        if not order_id:
            return "", 400

        threading.Thread(target=encolar_orden, args=(order_id,), daemon=True).start()
        return "", 200

    except Exception as e:
        logging.exception(f"💥 Error en webhook: {str(e)}")
        return "", 500

# 🔁 Función que procesa órdenes desde Redis
def worker_loop():
    logging.info("👷 Worker iniciado!!!")
    models, db, uid, password = connect_odoo()
    logging.info("👷 Worker conectado a Odoo")
    while True:
        try:
            item = r.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, order_id = item
                logging.info(f"📥 Procesando orden {order_id} desde {QUEUE_KEY}")
                procesar_orden(order_id, models, db, uid, password)
                logging.info(f"✅ Orden {order_id} procesada")
        except Exception as e:
            logging.exception(f"💥 Error en worker: {str(e)}")
        time.sleep(30)
        logging.info("👷 Worker en espera...")

def encolar_orden(order_id):
    try:
        logging.info(f"🧵 Hilo encolar_orden iniciado para orden {order_id}")
        r.lpush(QUEUE_KEY, order_id)
        logging.info(f"🗃 Orden {order_id} encolada en Redis (hilo)")
    except Exception as e:
        logging.exception(f"💥 Error encolando orden {order_id}: {e}")

# 🔁 Tarea periódica para ajustes de inventario
def ajuste_inventario():
    logging.info("🚀 Ajuste de inventario - Iniciado...")
    models, db, uid, password = connect_odoo()
    logging.info("🚀 Ajuste de inventario - Conectado a Odoo")
    while True:
        try:
            logging.info("⏱ Ejecutando tarea periódica...")
            ajustes_inventario_pendientes(models, db, uid, password)
        except Exception as e:
            logging.exception(f"💥 Error en tarea periódica: {str(e)}")
        time.sleep(60)

# 🔧 Lógica de procesamiento de orden
def procesar_orden(order_id, models, db, uid, password):
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

        client_id_odoo = get_client_id_by_dni(client_dni, client_name, client_email, models, db, uid, password)
        date = datetime.now()
        order_sale_id_odoo = create_sales_order(client_id_odoo, date, models, db, uid, password)
        logging.info(f"🧾 Orden de venta creada en Odoo: {order_sale_id_odoo}")

        for producto in order_data.get("products_data", []):
            sku = producto.get("sku")
            quantity = int(producto.get("quantity", 0))
            price = float(producto["price"]) if producto.get("price") else 0.0
            cargar_producto_a_orden_de_venta(order_sale_id_odoo, sku, quantity, price, models, db, uid, password)
            logging.info(f"➕ Producto agregado: SKU={sku}, cantidad={quantity}, precio={price}")

        confirm_sales_order(order_sale_id_odoo, models, db, uid, password)
        logging.info(f"✅ Orden de venta confirmada en Odoo: {order_sale_id_odoo}")

        order_name = get_order_name_by_id(order_sale_id_odoo, models, db, uid, password)
        affected_products = get_skus_and_stock_from_order(order_name, models, db, uid, password)
        skus_componentes = [p["default_code"] for p in affected_products]
        affected_kits = get_affected_kits_by_components(skus_componentes, models, db, uid, password)

        final_sku_list = affected_products + affected_kits
        skus_unicos = {item["default_code"]: item for item in final_sku_list}
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

# 🧵 Lanzar worker y tarea periódica al importar el módulo (Render usa gunicorn app:app)
time.sleep(2)  # ⏳ Esperar a que Gunicorn estabilice
threading.Thread(target=worker_loop, daemon=True).start()
threading.Thread(target=ajuste_inventario, daemon=True).start()
