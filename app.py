# app.py
import os
import threading
import time
import redis
from flask import Flask, request, jsonify

app = Flask(__name__)
app.logger.setLevel("INFO")  # Mostrar logs en Render

# --- Redis ---
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL no está definida")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
QUEUE_KEY = "ordenes_pendientes"

# --- Endpoint webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    order_id = data.get("id")

    if not order_id:
        return jsonify({"error": "Falta order_id"}), 400

    r.lpush(QUEUE_KEY, order_id)
    app.logger.info(f"🗃 Orden {order_id} encolada en Redis")
    return jsonify({"status": "ok", "order_id": order_id})


# --- Worker ---
def worker_loop():
    app.logger.info("👷 Worker iniciado, esperando órdenes...")
    while True:
        try:
            item = r.brpop(QUEUE_KEY, timeout=5)
            if item:
                queue, order_id = item
                app.logger.info(f"📥 Procesando orden {order_id} desde {queue}")
                time.sleep(2)
                app.logger.info(f"✅ Orden {order_id} procesada")
        except Exception as e:
            app.logger.error(f"❌ Error en worker: {e}")
            time.sleep(5)

# Lanzar worker incluso con Gunicorn
def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()

start_worker()
