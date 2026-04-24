import time
import logging
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# OBTENGO DATOS DE TN TEST
#STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
#TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
#API_URL = os.getenv("TIENDANUBE_URL")

# OBTENGO DATOS DE TN PURA
STORE_ID = os.getenv("TIENDANUBE_PRINTIMATES_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN")
API_URL = os.getenv("TIENDANUBE_URL")


def get_product_by_sku_tn(sku):
    url = f"{API_URL}/{STORE_ID}/products?q={sku}"

    headers = {
        "Authentication": f"bearer {TOKEN}",
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json"
    }

    max_retries = 3
    retries = 0
    delay = 2  # segundos entre intentos

    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                logging.error(f"❌ Error {response.status_code} al buscar SKU={sku}: {response.text}")
                retries += 1
                time.sleep(delay)
                continue

            productos = response.json()

            if not productos:
                logging.warning(f"❌ Intento {retries+1}/{max_retries}: No se encontró ningún producto con SKU={sku}.")
                retries += 1
                time.sleep(delay)
                continue

            producto = productos[0]  # Tomamos el primero que coincide
            id_padre = producto["id"]

            for variante in producto.get("variants", []):
                if variante.get("sku") == sku:
                    datos = {
                        "id_padre": id_padre,
                        "id": variante["id"],
                        "sku": variante["sku"],
                        "price": variante.get("price"),
                        "stock": variante["inventory_levels"][0]["stock"] if variante.get("inventory_levels") else None,
                        "values": [v.get("es") for v in variante.get("values", [])],
                        "producto_id": producto["id"],
                        "nombre": producto["name"].get("es"),
                        "url": producto.get("canonical_url")
                    }
                    return datos

            logging.warning(f"❌ Intento {retries+1}/{max_retries}: No se encontró ninguna variante exacta con SKU={sku}.")
            retries += 1
            time.sleep(delay)

        except Exception as e:
            logging.exception(f"💥 Error inesperado buscando SKU={sku}: {str(e)}")
            retries += 1
            time.sleep(delay)

    logging.error(f"💥 No se pudo obtener producto con SKU={sku} después de {max_retries} intentos.")
    return None

def update_stock_by_sku(sku, stock):
    # 🚫 Control de stock inválido
    if stock < 0:
        logging.warning(f"⚠️ Stock recibido inválido ({stock}) para SKU={sku} -> Se ajusta a 0. ")
        stock = 0  # Forzar stock a 0

    product = get_product_by_sku_tn(sku)
    if not product:
        logging.warning(f"❌ No se encontró producto con SKU {sku} en TiendaNube. No se actualizó stock.")
        return

    id_padre = product["id_padre"]
    id = product["id"]
    
    url = f"{API_URL}/{STORE_ID}/products/{id_padre}/variants/stock"
    headers = {
        "Authentication": f"bearer {TOKEN}",
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json"
    }

    payload = {
        "action": "replace",
        "value": stock,
        "id": id
    }

    max_retries = 5
    retries = 0
    while retries < max_retries:
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            logging.info(f"✅ Stock actualizado a {stock} para producto {product['nombre']} (SKU={sku})")
            return
        elif response.status_code == 429:
            wait_time = 2 ** retries  # backoff exponencial: 1s, 2s, 4s, 8s, 16s
            logging.warning(f"⚠️ Rate limit alcanzado (429) para SKU={sku}. Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
            retries += 1
        else:
            logging.error(f"❌ Error al actualizar stock SKU={sku}: {response.status_code} - {response.text}")
            return

    # Si llega acá, agotó los intentos
    logging.error(f"💥 No se pudo actualizar stock de SKU={sku} después de {max_retries} intentos. Se continúa con el resto.")
