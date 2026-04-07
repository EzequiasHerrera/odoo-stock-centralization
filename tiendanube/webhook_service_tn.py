import requests
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# --- TIENDANUBE TEST
#ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
#STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")

# --- TIENDANUBE PURAINTIMATES
ACCESS_TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN")
STORE_ID = os.getenv("TIENDANUBE_PRINTIMATES_ID")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")     # + "/webhook"


#Funcion que solamente se debe ejecutar para registrar Webhooks en la tienda
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


# Listar webhooks existentes
def listar_webhooks():
    BASE_URL = f"https://api.tiendanube.com/v1/{STORE_ID}/webhooks"
    HEADERS = {
        #"Authorization": f"bearer {ACCESS_TOKEN}",  # corregido por Copilot
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json",
    }

    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code == 200:
        webhooks = response.json()
        if not webhooks:
            print("⚠️ No hay webhooks configurados.")
        else:
            print("📋 Webhooks configurados:")
            for wh in webhooks:
                print(f"- ID: {wh.get('id')} | Evento: {wh.get('event')} | URL: {wh.get('url')}")
    else:
        print("❌ Error al listar los Webhooks")
        print("🔍 Código:", response.status_code)
        print("📄 Detalles:", response.text)
        
def eliminar_webhook(webhook_id):
    url = f"https://api.tiendanube.com/v1/{STORE_ID}/webhooks/{webhook_id}"
    headers = {
        "Content-Type": "application/json",
        "Authentication": f"bearer {ACCESS_TOKEN}",  # usá el que ya comprobaste que funciona
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)"
    }

    response = requests.delete(url, headers=headers)
    if response.status_code in (200, 204):
        print(f"🗑️ Webhook {webhook_id} eliminado correctamente.")
    else:
        print("❌ Error al eliminar el Webhook")
        print("🔍 Código:", response.status_code)
        print("📄 Detalles:", response.text)


def obtener_orden_por_id(order_id):
    url = f"https://api.tiendanube.com/v1/{STORE_ID}/orders/{order_id}"
    headers = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        orden = response.json()
        print("✅ Orden obtenida correctamente")
        # Mostrar todo el payload en consola
        import json
        print(json.dumps(orden, indent=4, ensure_ascii=False))
        return orden
    else:
        print(f"❌ Error al obtener la orden {order_id}")
        print("🔍 Código:", response.status_code)
        print("📄 Detalles:", response.text)
        return None


if __name__ == "__main__":
#    registrar_webhook("order/paid")
#    registrar_webhook("product/created")
    listar_webhooks()
#    eliminar_webhook(35789594)  # reemplazá con el ID real
#    listar_webhooks()

#    orden_id = 1941130901
#    obtener_orden_por_id(orden_id)