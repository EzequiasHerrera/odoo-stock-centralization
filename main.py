import os
import xmlrpc.client
from dotenv import load_dotenv
from clientes import crear_cliente_si_no_existe
from productos import buscar_producto_por_sku
from ventas import consultar_orden_de_venta, crear_orden_de_venta, obtener_skus_y_stock

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Datos de conexión a tu instancia de Odoo
url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USER")
password = os.getenv("ODOO_PASS")

# Clase personalizada para transporte seguro HTTPS
class SafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, use_datetime=False):
        super().__init__(use_datetime=use_datetime)

transport = SafeTransport()

# Conexión al servidor y autenticación
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", transport=transport)
uid = common.authenticate(db, username, password, {})

if not uid:
    print("❌ Error al conectar. Verificá los datos.")
    exit()

print(f"✅ Conectado correctamente. UID: {uid}")

# Conexión al modelo de objetos
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", transport=transport)

# Bucle interactivo
while True:
    print("\n🧪 ¿Qué querés testear?")
    print("1️⃣ Buscar producto por SKU")
    print("2️⃣ Consultar orden de venta por nombre")
    print("3️⃣ Crear una orden de venta con dos productos")
    print("4️⃣ Obtener SKUs y stock desde una orden de venta")
    print("9️⃣ Salir del programa")

    opcion = input("👉 Ingresá el número de opción (1, 2, 3, 4 o 9): ")

    if opcion == "1":
        sku = input("SKU: ")
        buscar_producto_por_sku(models, db, uid, password, sku)
    elif opcion == "2":
        consultar_orden_de_venta(models, db, uid, password)
    elif opcion == "3":
        crear_orden_de_venta(models, db, uid, password)
    elif opcion == "4":
        nombre_orden = input("🧾 Ingresá el nombre de la orden de venta (ej. S00003): ")
        productos = obtener_skus_y_stock(models, db, uid, password, nombre_orden)
        print("\n📦 Productos con stock actualizado:")
        for p in productos:
            print(f"SKU: {p['default_code']} | Stock disponible: {p['virtual_available']}")
    elif opcion == "9":
        print("👋 ¡Hasta la próxima!")
        break
    else:
        print("❌ Opción inválida.")
