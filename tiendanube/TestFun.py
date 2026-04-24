import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Configuración de TiendaNube
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

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error {response.status_code}: {response.text}")
        return None

    productos = response.json()
    if not productos:
        print(f"❌ TiendaNube no devolvió productos para query q={sku}.")
        return None

    # Recorro todos los productos devueltos
    for producto in productos:
        id_padre = producto["id"]

        # Mostrar todas las variantes devueltas
        print(f"🔎 Producto encontrado: {producto['name']['es']} (ID={id_padre})")
        print("➡️ Variantes devueltas:")
        for v in producto.get("variants", []):
            print(f"   - SKU={v.get('sku')} | stock={v.get('inventory_levels',[{}])[0].get('stock')}")

        # Comparación exacta (con strip/lower para evitar espacios o mayúsculas)
        for variante in producto.get("variants", []):
            if variante.get("sku", "").strip().lower() == sku.strip().lower():
                datos = {
                    "id_padre": id_padre,
                    "id": variante["id"],
                    "sku": variante["sku"],
                    "price": variante.get("price"),
                    "stock": variante.get("inventory_levels",[{}])[0].get("stock"),
                    "values": [v.get("es") for v in variante.get("values", [])],
                    "producto_id": producto["id"],
                    "nombre": producto["name"]["es"],
                    "url": producto.get("canonical_url")
                }
                return datos

    print(f"❌ No se encontró ninguna variante con SKU exacto={sku}.")
    return None

def update_stock_by_sku(sku, stock):
    product = get_product_by_sku_tn(sku)
    if not product:
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

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        print(f"✅ Stock actualizado a {stock} para producto {product['nombre']}")
    else:
        print(f"❌ Error al actualizar stock: {response.status_code} - {response.text}")

def main():
    sku = input("Ingrese el SKU del producto: ").strip()
    producto = get_product_by_sku_tn(sku)

    if not producto:
        return

    print(f"📦 Producto: {producto['nombre']} (SKU: {producto['sku']})")
    print(f"🔢 Stock actual: {producto['stock']}")

    try:
        nuevo_stock = int(input("Ingrese el nuevo stock: ").strip())
    except ValueError:
        print("❌ Stock inválido, debe ser un número entero.")
        return

    update_stock_by_sku(sku, nuevo_stock)

    # Verificamos nuevamente
    producto_actualizado = get_product_by_sku_tn(sku)
    if producto_actualizado:
        print(f"🔄 Stock leído después de la actualización: {producto_actualizado['stock']}")

if __name__ == "__main__":
    main()
