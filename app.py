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
from odoo.connect_odoo import conectar_con_reintentos
#from odoo.products_service_odoo import get_affected_kits_by_components
from odoo.precarga_boms import precargar_boms
from odoo.clients_service_odoo import get_client_id_by_dni
from odoo.sync_api import ajustes_inventario_pendientes
from odoo.orders_service_odoo import (
    create_sales_order,
    confirm_sales_order,
    cargar_producto_a_orden_de_venta,
    get_order_name_by_id,
    get_skus_and_stock_from_order
)

# --- Cargar variables de entorno si no estoy en Render ---
if os.getenv("RENDER") is None:
    from dotenv import load_dotenv
    load_dotenv()

# Leer la variable de entorno (por defecto False si no está definida)
impactar_tn = os.getenv("IMPACTAR_TN", "False").lower() == "true"

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
try:
    r.ping()
    logging.info("✅ Redis conectado correctamente")
except Exception as e:
    logging.exception(f"💥 Error conectando a Redis: {e}")

# 🔐 Verificación de firma HMAC para asegurar que el webhook proviene de TiendaNube
def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)

@app.route("/", methods=["GET"])
def index():
    return "🟢 Odoo Stock Centralization está activo", 200

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

@app.route("/webhook_odoo_confirmacion", methods=["POST"])
def webhook_odoo_confirmacion():
    try:
        data = request.get_json(force=True)
        order_name = data.get("name") or data.get("id")

        if not order_name:
            logging.warning(f"❌ Campo 'name' o 'id' faltante en payload: {data}")
            return "❌ name/id faltante", 400

        logging.info(f"📨 Webhook recibido desde Odoo: orden {order_name}")

        # Encolar directamente (más simple y confiable que con hilo)
        encolar_orden(order_name)

        return "✅ Webhook recibido", 200

    except Exception as e:
        logging.exception(f"💥 Error en webhook_odoo_confirmacion: {str(e)}")
        return "💥 Error interno", 500

@app.route("/webhook_odoo_cancelacion", methods=["POST"])
def webhook_odoo_cancelacion():
    try:
        data = request.get_json(force=True)
        order_name = data.get("name") or data.get("id")

        if not order_name:
            logging.warning(f"❌ Campo 'name' o 'id' faltante en payload: {data}")
            return "❌ name/id faltante", 400

        # Agregar la "C" al final del order_name
        order_name_cancel = f"{order_name}C"
        logging.info(f"📨 Webhook recibido desde Odoo (cancelación): orden {order_name_cancel}")

        # Encolar directamente
        encolar_orden(order_name_cancel)

        return "✅ Webhook de cancelación recibido", 200

    except Exception as e:
        logging.exception(f"💥 Error en webhook_odoo_cancelacion: {str(e)}")
        return "💥 Error interno", 500


# 🔁 Función que procesa órdenes desde Redis
def worker_loop():
    logging.info("👷 Worker iniciado!!!")
    models, db, uid, password = conectar_con_reintentos()
    if not all([models, db, uid, password]):
        logging.error("❌ Abortando worker por fallo de conexión")
        return

    logging.info("👷 Worker conectado a Odoo")

    # Precargar BOMs una sola vez al inicio del servidor
    global BOM_CACHE
    BOM_CACHE = precargar_boms(models, db, uid, password)
    logging.info("📦 BOM_CACHE inicializado y listo para consultas")

    while True:
        try:
            item = r.brpop(QUEUE_KEY, timeout=5)
            if item:
                _, order_id = item
                logging.info(f"📥 Procesando orden {order_id} desde {QUEUE_KEY}")

                if order_id.startswith("S"):
                    if order_id.endswith("C"):
                        logging.info(f"🔁 Orden {order_id} detectada como CANCELACIÓN en Odoo")
                        # Remover la "C" final antes de enviar a Odoo
                        # order_name = order_id[:-1]
                    else:
                        logging.info(f"🔁 Orden {order_id} detectada como CONFIRMACIÓN en Odoo")
                        # order_name = order_id

                    order_name = order_id
                    procesar_orden_odoo(order_name, models, db, uid, password, BOM_CACHE)

                else:
                    logging.info(f"🔁 Orden {order_id} detectada como TiendaNube")
                    procesar_orden(order_id, models, db, uid, password, BOM_CACHE)

                logging.info(f"✅ Orden {order_id} procesada")
        except Exception as e:
            logging.exception(f"💥 Error en worker: {str(e)}")

        time.sleep(30)
        logging.info("👷 Worker buscando ordenes de venta pendientes.")


def encolar_orden(order_id):
    logging.info(f"🧵 Hilo encolar_orden iniciado para orden {order_id}")

    if not order_id:
        logging.error("❌ order_id no válido. Abortando encolado.")
        return

    try:
        # Verificar conexión a Redis
        r.ping()
        logging.info("✅ Redis está accesible desde encolar_orden")

        # Encolar la orden
        resultado = r.lpush(QUEUE_KEY, order_id)
        if resultado > 0:
            logging.info(f"🗃 Orden {order_id} encolada correctamente en Redis (posición {resultado})")
        else:
            logging.warning(f"⚠️ Redis devolvió resultado inesperado al encolar orden {order_id}: {resultado}")

    except Exception as e:
        logging.exception(f"💥 Error encolando orden {order_id}: {e}")

# 🔁 Tarea periódica para ajustes de inventario
def ajuste_inventario():
    logging.info("🚀 Ajuste de inventario - Iniciado...")
    models, db, uid, password = conectar_con_reintentos()
    if not all([models, db, uid, password]):
        logging.error("❌ Abortando tarea de ajuste por fallo de conexión")
        return

    logging.info("🚀 Ajuste de inventario - Conectado a Odoo")

    # 🔄 Precargar BOM_CACHE aquí
    global BOM_CACHE
    BOM_CACHE = precargar_boms(models, db, uid, password)
    logging.info("📦 BOM_CACHE inicializado para tarea de ajuste de inventario")

    while True:
        try:
#            logging.info("⏱ Ejecutando tarea periódica...")
            if impactar_tn: 
                ajustes_inventario_pendientes(models, db, uid, password, BOM_CACHE)
            else:
                logging.info("⚠️ Simulación: NO se hace ajuste de inventario")
        except Exception as e:
            logging.exception(f"💥 Error en tarea periódica: {str(e)}")
        time.sleep(60)

# 🔧 Lógica de procesamiento de orden
def procesar_orden(order_id, models, db, uid, password, BOM_CACHE):
    if not verificar_idempotencia(order_id, r):
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
        
        order_number = order_data.get("order_number") or ""
        order_sale_id_odoo = create_sales_order(client_id_odoo, date, models, db, uid, password, order_number)
        logging.info(f"🧾 Orden de venta creada en Odoo: {order_sale_id_odoo} (TiendaNube #{order_number})")

        for producto in order_data.get("products_data", []):
            sku = producto.get("sku")
            quantity = int(producto.get("quantity", 0))
            price = float(producto["price"]) if producto.get("price") else 0.0

            # 🚫 Validación: SKU faltante
            if not sku or not isinstance(sku, str):
                logging.error(f"❌ Producto inválido en orden {order_id}: SKU vacío o incorrecto. Se omitió este registro.")
                continue

            cargar_producto_a_orden_de_venta(order_sale_id_odoo, sku, quantity, price, models, db, uid, password)
            logging.info(f"➕ Producto agregado: SKU={sku}, cantidad={quantity}, precio={price}")

        # Agregar descuento global si existe
        discount_total = order_data.get("discount_total", 0)
        if discount_total > 0:
            cargar_producto_a_orden_de_venta(order_sale_id_odoo, "DESCUENTO_GLOBAL", 1, -discount_total, models, db, uid, password)
            logging.info(f"💸 Descuento global aplicado: -{discount_total}")

        # Agregar costo de envío si existe
        shipping_cost = order_data.get("shipping_cost", 0)
        if shipping_cost > 0:
            cargar_producto_a_orden_de_venta(order_sale_id_odoo, "COSTO_ENVIO", 1, shipping_cost, models, db, uid, password)
            logging.info(f"🚚 Costo de envío agregado: {shipping_cost}")

        confirm_sales_order(order_sale_id_odoo, models, db, uid, password)
        logging.info(f"✅ Orden de venta confirmada en Odoo: {order_sale_id_odoo}")

        order_name = get_order_name_by_id(order_sale_id_odoo, models, db, uid, password)
        affected_products = get_skus_and_stock_from_order(order_name, models, db, uid, password)

        skus_componentes = [p["default_code"] for p in affected_products]

 
        # Expandir kits (convertir cada SKU en dict con default_code)
        affected_kits = []
        for sku in skus_componentes:
            affected_kits.extend(BOM_CACHE.get(sku, []))

        final_sku_list = affected_products + affected_kits
        skus_unicos = {item["default_code"]: item for item in final_sku_list}
        lista_final_sin_duplicados = list(skus_unicos.values())

        # 🔄 Refrescar stock desde Odoo para la lista final
        product_ids = [item["id"] for item in lista_final_sin_duplicados if "id" in item]
        if product_ids:
            productos_actualizados = models.execute_kw(
                db, uid, password,
                "product.product", "read",
                [product_ids],
                {"fields": ["id", "default_code", "virtual_available"]}
            )
            productos_por_id = {p["id"]: p for p in productos_actualizados}
            for item in lista_final_sin_duplicados:
                if "id" in item and item["id"] in productos_por_id:
                    item["virtual_available"] = productos_por_id[item["id"]]["virtual_available"]

        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_sin_duplicados]}")

        # Ordenar lista: primero SKUs que NO son de Funsales (no contienen "|"), luego los de Funsales
        lista_final_sin_duplicados = sorted(
            lista_final_sin_duplicados,
            key=lambda item: "|" in str(item.get("default_code", ""))
        )

        for producto in lista_final_sin_duplicados:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)

            # 🚫 Validación: SKU faltante o inválido
            if not sku or not isinstance(sku, str):
                logging.error(
                    f"❌ Producto con ID={producto.get('id','N/A')} no tiene SKU válido. "
                    f"Se omitió este registro."
                )
                continue
    
            # ⚠️ No actualizar SKUs especiales (descuento/envío)
            if sku in ["DESCUENTO_GLOBAL", "COSTO_ENVIO"]:
                logging.info(f"⏭️ SKU {sku} omitido (línea especial de descuento/envío). Stock actual: {stock}")
                continue

            if impactar_tn:
                update_stock_by_sku(sku, stock)
                time.sleep(0.5)

            else:
                logging.info(f"⚠️ Simulación: NO se actualizó en TiendaNube. SKU={sku}, stock={stock}")

        logging.info(f"🎯 Orden {order_id} procesada exitosamente.")

    except Exception as e:
        logging.exception(f"💥 Error procesando la orden {order_id}: {str(e)}")


# 🔧 Lógica de procesamiento de orden
def procesar_orden_odoo(order_name, models, db, uid, password, BOM_CACHE):
    if not verificar_idempotencia(order_name, r):
        logging.warning(f"⚠️ Orden {order_name} ya fue procesada previamente. Abortando.")
        return

    try:
        if order_name.endswith("C"):
            # Remover la "C" final antes de enviar a Odoo
            order_name = order_name[:-1]
            logging.info(f"✅ Orden de venta cancelada desde Odoo: {order_name}")
        else:
            logging.info(f"✅ Orden de venta a procesar desde Odoo: {order_name}")

        affected_products = get_skus_and_stock_from_order(order_name, models, db, uid, password)
        skus_componentes = [p["default_code"] for p in affected_products]

        # Expandir kits (convertir cada SKU en dict con default_code)
        affected_kits = []
        for sku in skus_componentes:
            affected_kits.extend(BOM_CACHE.get(sku, []))

        final_sku_list = affected_products + affected_kits
        skus_unicos = {item["default_code"]: item for item in final_sku_list}
        lista_final_sin_duplicados = list(skus_unicos.values())

        # 🔄 Refrescar stock desde Odoo para la lista final
        product_ids = [item["id"] for item in lista_final_sin_duplicados if "id" in item]
        if product_ids:
            productos_actualizados = models.execute_kw(
                db, uid, password,
                "product.product", "read",
                [product_ids],
                {"fields": ["id", "default_code", "virtual_available"]}
            )
            productos_por_id = {p["id"]: p for p in productos_actualizados}
            for item in lista_final_sin_duplicados:
                if "id" in item and item["id"] in productos_por_id:
                    item["virtual_available"] = productos_por_id[item["id"]]["virtual_available"]

        logging.info(f"📦 Lista final de SKUs a actualizar: {[p['default_code'] for p in lista_final_sin_duplicados]}")

        # Ordenar lista: primero SKUs que NO son de Funsales (no contienen "|"), luego los de Funsales
        lista_final_sin_duplicados = sorted(
            lista_final_sin_duplicados,
            key=lambda item: "|" in str(item.get("default_code", ""))
        )

        for producto in lista_final_sin_duplicados:
            sku = producto.get("default_code")
            stock = producto.get("virtual_available", 0.0)

            # 🚫 Validación: SKU faltante o inválido
            if not sku or not isinstance(sku, str):
                logging.error(
                    f"❌ Producto con ID={producto.get('id','N/A')} no tiene SKU válido. "
                    f"Se omitió este registro."
                )
                continue

            # ⚠️ No actualizar SKUs especiales (descuento/envío)
            if sku in ["DESCUENTO_GLOBAL", "COSTO_ENVIO"]:
                logging.info(f"⏭️ SKU {sku} omitido (línea especial de descuento/envío). Stock actual: {stock}")
                continue

            if impactar_tn:
                update_stock_by_sku(sku, stock)
                time.sleep(0.5)

            else:
                logging.info(f"⚠️ Simulación: NO se actualizó en TiendaNube. SKU={sku}, stock={stock}")

        logging.info(f"🎯 Orden {order_name} procesada exitosamente.")

    except Exception as e:
        logging.exception(f"💥 Error procesando la orden {order_name}: {str(e)}")


# 🧵 Lanzar worker y tarea periódica al importar el módulo (Render usa gunicorn app:app)
time.sleep(5)  # ⏳ Esperar a que Gunicorn estabilice
threading.Thread(target=worker_loop, daemon=True).start()
threading.Thread(target=ajuste_inventario, daemon=True).start()