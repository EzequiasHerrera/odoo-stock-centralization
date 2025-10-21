import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("TIENDANUBE_URL");
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
SKU = "Test-ProB-Blan-S"

def get_product_by_sku_tn(sku):
    url = f"{API_URL}/{STORE_ID}/products?q={sku}"

    headers = {
        "Authentication": f"bearer {TOKEN}",
        "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

    productos = response.json()

    if not productos:
        print("❌ No se encontró ningún producto con ese SKU.")
        return None

    producto = productos[0]  # Tomamos el primero que coincide
    id_padre = producto["id"];

    for variante in producto["variants"]:
        if variante["sku"] == sku:
            datos = {
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
            return datos

    print("❌ No se encontró ninguna variante con ese SKU exacto.")
    return None

def update_stock_by_sku(sku, stock):
    product = get_product_by_sku_tn(sku);
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

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print(f"✅ Stock actualizado a {stock} para producto {product['nombre']}")
    else:
        print(f"❌ Error al actualizar stock: {response.status_code} - {response.text}")