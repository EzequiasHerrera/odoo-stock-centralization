import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + "/webhook"

def registrar_webhook(webhookName):
    url = f"https://api.tiendanube.com/v1/{STORE_ID}/webhooks"
    headers = {
        "Content-Type": "application/json",
        "Authentication": f"bearer {ACCESS_TOKEN}"
    }
    data = {
        "url": WEBHOOK_URL,
        "event": webhookName
    }

    logging.info(f"📡 Intentando registrar webhook para evento: {webhookName}")

    try:
        response = requests.post(url, json=data, headers=headers)
    except Exception as e:
        logging.exception("💥 Error de red al registrar el webhook")
        return

    if response.status_code == 201:
        logging.info("✅ Webhook registrado correctamente")
        logging.info(f"📦 Respuesta: {response.json()}")
    else:
        logging.error("❌ Error al registrar el Webhook")
        logging.error(f"🔍 Código: {response.status_code}")
        logging.error(f"📄 Detalles: {response.text}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    registrar_webhook("order/paid")
