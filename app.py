# Esta va a ser la función principal que maneje los webhooks y actúe en consecuencia
from flask import Flask, request, abort
import os
import hmac
import hashlib
from odoo.connect_odoo import connect_odoo
from dotenv import load_dotenv
from tiendanube.orders_service_tn import extract_order_data
from tiendanube.orders_service_tn import get_order_by_id
from odoo.clients_service_odoo import get_client_id_by_dni

load_dotenv()

# CONECTO CON ODOO
models, db, uid, password = connect_odoo()
if not uid:
    exit()

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
#----------------------------------------------------------TESTING ----------------------------------------------------------
# 🔁 Lógica reutilizable
def process_order(order_id):
    order = get_order_by_id(order_id)
    if not order:
        print(f"❌ No se pudo obtener la orden {order_id}")
        return None

    order_data = extract_order_data(order)
    print("✅ Datos extraídos:", order_data)
    return order_data

# 🧪 Testing manual sin Flask
if __name__ == "__main__":
    TEST_ORDER_ID = "1812732935"
    process_order(TEST_ORDER_ID)
