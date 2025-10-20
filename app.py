# Esta va a ser la función principal que maneje los webhooks y actúe en consecuencia
from flask import Flask, request, abort
import os
import hmac
import hashlib
from odoo.connect_odoo import connect_odoo
from dotenv import load_dotenv
from tiendanube.orders_service_tn import extract_order_data

load_dotenv()
models, db, uid, password = connect_odoo()
if not uid:
    exit()

app = Flask(__name__)
APP_SECRET = os.getenv("TIENDANUBE_SECRET")


def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)


@app.route("/webhook", methods=["POST"])
def webhook():
    hmac_header = request.headers.get("x-linkedstore-hmac-sha256")
    raw_data = request.get_data()
    if not verify_signature(raw_data, hmac_header):
        abort(401, "Firma inválida")
    
    # {'store_id': 6384636, 'event': 'order/paid', 'id': 1812657530}
    data = request.json
    order_id = data.get('id')

    print("✅ Webhook recibido:", request.json)
    print(f"{extract_order_data(order_id)}")
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
