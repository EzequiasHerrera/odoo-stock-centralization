# idempotencia.py — Control de idempotencia usando Redis
import logging
import os

# Redis debe estar inicializado en app.py y pasado como parámetro
IDEMPOTENCY_PREFIX = "orden_procesada:"
IDEMPOTENCY_TTL_SECONDS = 604800  # 7 días en segundos

def verificar_idempotencia(order_id, redis_instance):
    """
    Verifica si la orden ya fue procesada. Si no, la marca como procesada.
    Devuelve True si es la primera vez que se procesa.
    """
    if not order_id:
        logging.warning("⚠️ order_id vacío en verificación de idempotencia")
        return False

    clave = f"{IDEMPOTENCY_PREFIX}{order_id}"

    try:
        if redis_instance.exists(clave):
            logging.info(f"🔁 Orden {order_id} ya fue procesada (idempotencia activa)")
            return False

        # Marcar como procesada con TTL
        redis_instance.setex(clave, IDEMPOTENCY_TTL_SECONDS, "1")
        logging.info(f"🆕 Orden {order_id} marcada como procesada en Redis (TTL={IDEMPOTENCY_TTL_SECONDS}s)")
        return True

    except Exception as e:
        logging.exception(f"💥 Error verificando idempotencia para orden {order_id}: {e}")
        return False
