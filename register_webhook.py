import requests
import os
from dotenv import load_dotenv
from pathlib import Path

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

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 201:
        print("✅ Webhook registrado correctamente")
        print("📦 Respuesta:", response.json())
    else:
        print("❌ Error al registrar el Webhook")
        print("🔍 Código:", response.status_code)
        print("📄 Detalles:", response.text)

if __name__ == "__main__":
    registrar_webhook("order/paid")