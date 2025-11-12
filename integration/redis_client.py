import redis
import os
import logging

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL no está definida")

try:
    r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    logging.info("✅ Redis conectado correctamente desde redis_client.py")
except Exception as e:
    logging.exception(f"💥 Error conectando a Redis: {e}")
