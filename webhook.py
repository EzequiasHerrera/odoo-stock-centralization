from flask import Flask, request, abort
import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
APP_SECRET = os.getenv("TIENDANUBE_SECRET")

def verify_signature(data, hmac_header):
    digest = hmac.new(APP_SECRET.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, hmac_header)

@app.route('/webhook', methods=['POST'])
def webhook():
    hmac_header = request.headers.get('x-linkedstore-hmac-sha256')
    raw_data = request.get_data()

    if not verify_signature(raw_data, hmac_header):
        abort(401, 'Firma inválida')

    print("✅ Webhook recibido:", request.json)
    return 'OK', 200

if __name__ == '__main__':
    app.run(port=3000)