# Esta va a ser la función principal que maneje los webhooks y actúe en consecuencia
from flask import Flask, request, abort
import os
import hmac
import hashlib
from dotenv import load_dotenv

from tiendanube.orders_service_tn import extract_order_data, get_order_by_id
from tiendanube.products_service_tn import update_stock_by_sku

from datetime import datetime

from odoo.products_service_odoo import get_affected_kits_by_components
from odoo.clients_service_odoo import get_client_id_by_dni
from odoo.orders_service_odoo import (
    create_sales_order,
    confirm_sales_order,
    cargar_producto_a_orden_de_venta,
    get_order_name_by_id,
    get_skus_and_stock_from_order
)


load_dotenv()

# OBTENGO DATOS DE TN
APP_SECRET = os.getenv("TIENDANUBE_SECRET")
STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")

app = Flask(__name__)


def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)


"""
@app.route("/webhook", methods=["POST"])
def webhook():
    hmac_header = request.headers.get("x-linkedstore-hmac-sha256")
    raw_data = request.get_data()
    if not verify_signature(raw_data, hmac_header):
        abort(401, "Firma inválida")
    # print("✅ Webhook recibido:", request.json)
    # {'store_id': 6384636, 'event': 'order/paid', 'id': 1812657530}

    data = request.json  # Transformo la respuesta HTTP en JSON

    # TIENDA NUBE
    # order_id = data.get("id")  # Extraigo el id de la orden
    order_id = "1812732935"  # ID Testing
    order = get_order_by_id(order_id)  # Utilizo el id para obtener la orden COMPLETA
    order_data = extract_order_data(order)  # Extraigo los datos RELEVANTES de la orden

    print(f"{order_data}")
    # ODOO
    # client_id_odoo = get_client_id_by_dni(order_data.get('client_data', {}).get('name'));
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    webhook();

"""


# ----------------------------------------------------------TESTING ----------------------------------------------------------
# 🔁 Lógica reutilizable
def webhook_testing():
    # TIENDA NUBE
    order_id = "1812732935"
    order = get_order_by_id(order_id)
    if not order:
        print(f"❌ No se pudo obtener la orden {order_id}")
        return None

    order_data = extract_order_data(order)

    # ODOO
    client_dni = order_data.get("client_data", {}).get("dni")
    client_name = order_data.get("client_data", {}).get("name")
    client_email = order_data.get("client_data", {}).get("email")

    client_id_odoo = get_client_id_by_dni(client_dni, client_name, client_email)
    date = datetime.now()  # Deberíamos traer date de los datos de orden de compra
    order_sale_id_odoo = create_sales_order(client_id_odoo, date)

    for producto in order_data.get("products_data", []):
        sku = producto.get("sku")
        quantity = int(producto.get("quantity", 0))
        price = float(producto["price"]) if producto.get("price") else 0.0
        
        cargar_producto_a_orden_de_venta(order_sale_id_odoo, sku, quantity, price)
    confirm_sales_order(order_sale_id_odoo);
    
    # Nueva funcion para obtener nombre de orden según ID
    order_name = get_order_name_by_id(order_sale_id_odoo)
    
    affected_products = get_skus_and_stock_from_order(order_name)
    skus_componentes = [p["default_code"] for p in affected_products]
    affected_kits = get_affected_kits_by_components(skus_componentes)

    # Unificar ambas listas
    final_sku_list = affected_products + affected_kits

    # Deduplicar por SKU
    skus_unicos = {}
    
    for item in final_sku_list:
        sku = item.get("default_code", "N/A")
        # Si el SKU ya está en el diccionario, lo ignoramos
        if sku not in skus_unicos:
            skus_unicos[sku] = item

    # Convertir de nuevo a lista
    lista_final_sin_duplicados = list(skus_unicos.values())

    print("\n📦 Lista final de SKUs a actualizar en TiendaNube:")
    for producto in lista_final_sin_duplicados:
        sku = producto.get("default_code", "N/A")
        stock = producto.get("virtual_available", 0.0)
        update_stock_by_sku(sku, stock)
    
# 🧪 Testing manual sin Flask
if __name__ == "__main__":
    webhook_testing()
