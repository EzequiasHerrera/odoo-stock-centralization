import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
TIENDANUBE_URL = os.getenv("TIENDANUBE_URL")

def extract_order_data(order_data):
    client = order_data.get('customer', {})
    client_data = {
        'id': client.get('id'),
        'name': client.get('name'),
        'phone': client.get('phone'),
        'dni': client.get('identification'),
        'email': client.get('email'),
    }

    shipping_info = order_data.get('shipping_address', {})
    shipping_data = {
        'address': shipping_info.get('address'),
        'province': shipping_info.get('province'),
        'city': shipping_info.get('city'),
        'locality': shipping_info.get('locality'),
        'floor': shipping_info.get('floor'),
        'number': shipping_info.get('number'),
        'zipcode': shipping_info.get('zipcode')
    }

    products = []
    for prod in order_data.get('products', []):
        products.append({
            'product_id': prod.get('product_id'),
            'name': prod.get('name_without_variants'),
            'sku': prod.get('sku'),
            'quantity': prod.get('quantity'),
            'price': prod.get('price'),
        })

    return {
        'client_data': client_data,
        'shipping_data': shipping_data,
        'products_data': products
    }

def get_order_by_id(order_id):
    url = f"{TIENDANUBE_URL}/{STORE_ID}/orders/{order_id}"
    headers = {
        "Authentication": f"bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        logging.exception(f"💥 Error de red al obtener la orden {order_id}")
        return None

    if response.status_code == 200:
        logging.info(f"📦 Orden {order_id} obtenida correctamente desde TiendaNube")
        return response.json()
    else:
        logging.error(f"❌ Error al obtener la orden {order_id}: {response.status_code} - {response.text}")
        return None
