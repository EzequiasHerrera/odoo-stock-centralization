import logging
from integration.redis_client import r

# Tiempo de expiración en segundos (7 días)
EXPIRACION_SEGUNDOS = 7 * 24 * 60 * 60  # 604800

def verificar_idempotencia(order_id):
    if not order_id:
        logging.error("❌ order_id no válido. Abortando verificación de idempotencia.")
        return False

    key = f"idempotente:orden:{order_id}"
    try:
        if r.exists(key):
            logging.info(f"🔁 Orden {order_id} ya fue procesada (idempotente)")
            return False

        r.set(key, "procesado", ex=EXPIRACION_SEGUNDOS)
        logging.info(f"✅ Orden {order_id} registrada como procesada (idempotencia)")
        return True

    except Exception as e:
        logging.exception(f"💥 Error verificando idempotencia para orden {order_id}: {e}")
        return False
