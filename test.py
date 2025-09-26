import os
import xmlrpc.client
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Datos de tu instancia
url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USER")
password = os.getenv("ODOO_PASS")

# Transporte seguro para HTTPS
class SafeTransport(xmlrpc.client.SafeTransport):
    def __init__(self, use_datetime=False):
        super().__init__(use_datetime=use_datetime)

transport = SafeTransport()

# Conexión al servidor
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", transport=transport)

# Autenticación
uid = common.authenticate(db, username, password, {})

if uid:
    print(f"✅ Conectado correctamente. UID: {uid}")
else:
    print("❌ Error al conectar. Verificá los datos.")
    exit()

# Conexión a los modelos
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", transport=transport)

# Buscar producto por código interno
sku = "010130101"
product_ids = models.execute_kw(db, uid, password,
    'product.product', 'search',
    [[['default_code', '=', sku]]], {'limit': 1})

if product_ids:
    product = models.execute_kw(db, uid, password,
        'product.product', 'read', [product_ids])
    print("📦 Producto encontrado:")
    print("Nombre:", product[0]['name'])
    print("Stock disponible:", product[0]['qty_available'])
else:
    print("❌ Producto no encontrado.")