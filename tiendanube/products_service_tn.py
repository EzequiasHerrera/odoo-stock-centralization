import os
import requests
import json
import logging
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("TIENDANUBE_URL")
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")

def get_product_by_sku_tn(sku):
    url = f"{API_URL}/{STORE_ID}/products?q={sku}"
    headers = {
        "Authentication": f"bearer {TOKEN}",
        "User-Agent": "OdooSyncBot (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        logging.exception(f"💥 Error de red al buscar producto con SKU {sku}")
        return None

    if response.status_code != 200:
        logging.error(f"❌ Error {response.status_code}: {response.text}")
        return None

    productos = response.json()
    if not productos:
        logging.warning(f"❌ No se encontró ningún producto con SKU '{sku}'")
        return None

    producto = productos[0]
    id_padre = producto["id"]

    for variante in producto["variants"]:
        if variante["sku"] == sku:
            return {
                "id_padre": id_padre,
                "id": variante["id"],
                "sku": variante["sku"],
                "price": variante["price"],
                "stock": variante["inventory_levels"][0]["stock"],
                "values": [v["es"] for v in variante["values"]],
                "producto_id": producto["id"],
                "nombre": producto["name"]["es"],
                "url": producto["canonical_url"]
            }

    logging.warning(f"❌ No se encontró variante exacta con SKU '{sku}'")
    return None

def update_stock_by_sku(sku, stock):
    product = get_product_by_sku_tn(sku)
    if not product:
        logging.warning(f"⚠️ No se pudo obtener producto con SKU {sku} para actualizar stock.")
        return

    id_padre = product["id_padre"]
    id = product["id"]
    url = f"{API_URL}/{STORE_ID}/products/{id_padre}/variants/stock"
    headers = {
        "Authentication": f"bearer {TOKEN}",
        "User-Agent": "OdooSyncBot (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json"
    }

    payload = {
        "action": "replace",
        "value": stock,
        "id": id
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
    except Exception as e:
        logging.exception(f"💥 Error de red al actualizar stock para SKU {sku}")
        return

    if response.status_code == 200:
        logging.info(f"{url}")
        logging.info(f"✅ Stock actualizado a {stock} para producto {product['nombre']}")
    else:
        logging.error(f"❌ Error al actualizar stock: {response.status_code} - {response.text}")
