import sys
import os
import xmlrpc.client
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from productos import buscar_producto_por_sku
from tiendanube.products_service_tn import update_stock_by_sku


load_dotenv()

url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USER")
password = os.getenv("ODOO_PASS")

class SafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, use_datetime=False):
        super().__init__(use_datetime=use_datetime)

transport = SafeTransport()
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", transport=transport)
uid = common.authenticate(db, username, password, {})

if not uid:
    print("❌ Error al conectar.")
    exit()

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", transport=transport)

# Esta funcion vamos a cambiarla para que reciba el SKU en cuestion, lo busque en Odoo, tome el stock y lo actualice en TN
def update_stock_on_tn_based_on_odoo(sku):
    odoo_product = buscar_producto_por_sku(models, db, uid, password, sku)
    
    if odoo_product:
        print(f"\nStock virtual de Odoo para {odoo_product['name']} - {odoo_product['sku']}: {odoo_product['stock_virtual']}")
        update_stock_by_sku(sku, odoo_product["stock_virtual"]);
    else:
        print("❌ Producto no encontrado.")




# Bucle interactivo
while True:
    print("\n🧪 ¿Qué querés testear?")
    print("1️⃣ Actualizar stock TN desde Odoo por SKU")
#    print("2️⃣ ")
#    print("3️⃣ ")
#    print("4️⃣ ")
#    print("5️⃣ ")
#    print("6️⃣ ")
#    print("7️⃣ ")
    print("9️⃣ Salir del programa")

    opcion = input("👉 Ingresá el número de opción: ")

    if opcion == "1":
        SKU = "Test-ProB-Blan-S"
        update_stock_on_tn_based_on_odoo(SKU);

    elif opcion == "2":
        print("\n📦 OPCION 2\n")

#    elif opcion == "3":
#    elif opcion == "4":
#    elif opcion == "5":
#    elif opcion == "6":
#    elif opcion == "7":

    elif opcion == "9":
        print("👋 ¡Hasta la próxima!\n")
        break
    else:
        print("❌ Opción inválida.")
