import os
import redis
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

QUEUE_KEY = "ordenes_pendientes"

# 1. Encolar varias órdenes
orders = ["1001", "1002", "1003"]
for oid in orders:
    r.lpush(QUEUE_KEY, oid)
    print(f"🗃 Encolada orden {oid}")

# 2. Consumir la cola en secuencia
print("📥 Consumidor esperando órdenes...")
while True:
    item = r.brpop(QUEUE_KEY, timeout=3)  # espera hasta 3 segundos
    if item:
        queue, value = item
        print(f"✅ Procesada orden desde {queue}: {value}")
    else:
        print("⏸ Cola vacía, fin de prueba.")
        break
