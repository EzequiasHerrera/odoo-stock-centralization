# app.py
import os
import threading
import time
import redis
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Cargar variables de entorno (.env en local, Render ya las inyecta)
load_dotenv()

app = Flask(__name__)

# Conexión a Redis (TLS con rediss://)
REDIS_URL = os.getenv("REDIS_URL")
QUEUE_KEY = "ordenes_pendientes"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


# --- Endpoint para recibir órdenes ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    order_id = data.get("id")

    if not order_id:
        return jsonify({"error": "Falta order_id"}), 400

    # Encolar la orden
    r.lpush(QUEUE_KEY, order_id)
    app.logger.info(f"🗃 Orden {order_id} encolada en Redis")
    return jsonify({"status": "ok", "order_id": order_id})


# --- Worker en segundo plano ---
def worker_loop():
    app.logger.info("👷 Worker iniciado, esperando órdenes...")
    while True:
        try:
            # BRPOP bloquea hasta que haya un item (timeout 5s para no colgarse)
            item = r.brpop(QUEUE_KEY, timeout=5)
            if item:
                queue, order_id = item
                app.logger.info(f"📥 Procesando orden {order_id} desde {queue}")
                # Simulación de procesamiento
                time.sleep(2)
                app.logger.info(f"✅ Orden {order_id} procesada")
        except Exception as e:
            app.logger.error(f"❌ Error en worker: {e}")
            time.sleep(5)


# Lanzar worker en un thread separado
def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()


# --- Main ---
if __name__ == "__main__":
    start_worker()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
