import os;
import requests;
from dotenv import load_dotenv

load_dotenv()

# OBTENGO DATOS DE TN TEST
#STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
#TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
#TIENDANUBE_URL = os.getenv("TIENDANUBE_URL")

# OBTENGO DATOS DE TN PURA
STORE_ID = os.getenv("TIENDANUBE_PRINTIMATES_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN")
TIENDANUBE_URL = os.getenv("TIENDANUBE_URL")

def extract_order_data(order_data):
    # Datos del Cliente
    client = order_data.get('customer', {})
    client_data = {
        'id': client.get('id'),
        'name': client.get('name'),
        'phone': client.get('phone'),
        'dni': client.get('identification'),
        'email': client.get('email'),
    }
    
    # Datos del Envío
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
    
    # Detalles de la Venta
    products = []
    for prod in order_data.get('products', []):
        products.append({
            'product_id': prod.get('product_id'),
            'name': prod.get('name_without_variants'),
            'sku': prod.get('sku'),
            'quantity': prod.get('quantity'),
            'price': prod.get('price'),
        })
    
    # Retornar objeto unificado
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

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error al obtener la orden {order_id}: {response.status_code} - {response.text}")
        return None