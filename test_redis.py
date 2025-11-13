import os
import redis
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

order_id = "1830512071"
idempotency_key = f"orden_procesada:{order_id}"

if r.exists(idempotency_key):
    ttl = r.ttl(idempotency_key)
    print(f"✅ La orden {order_id} está registrada como procesada. TTL restante: {ttl} segundos")
else:
    print(f"❌ La orden {order_id} no está registrada en Redis")
