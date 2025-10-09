import os
import requests
from dotenv import load_dotenv

load_dotenv()

STORE_ID = os.getenv("TIENDANUBE_TESTSTORE_ID")
TOKEN = os.getenv("TIENDANUBE_ACCESS_TOKEN_TEST")
SKU = "Test-ProB-Blan-S"

url = f"https://api.tiendanube.com/v1/{STORE_ID}/products?q={SKU}"

headers = {
    "Authentication": f"bearer {TOKEN}",
    "User-Agent": "Test Odoo (ezequiasherrera99@gmail.com)",
    "Content-Type": "application/json"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    productos = response.json()
    print(f"{productos}")
else:
    print(f"❌ Error {response.status_code}: {response.text}")

