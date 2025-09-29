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
sku = "Test-Kit-AB"
product_ids = models.execute_kw(db, uid, password,
    'product.product', 'search',
    [[['x_studio_sku', '=', sku]]], {'limit': 1})

if product_ids:
    product = models.execute_kw(db, uid, password,
        'product.product', 'read', [product_ids])
    print("📦 Producto encontrado:")
    print("Nombre:", product[0]['name'])
    print("Color:", product[0]['x_studio_color'])
    print("Talle:", product[0]['x_studio_talle'])
    print("Stock disponible:", product[0]['qty_available'])
else:
    print("❌ Producto no encontrado.")


# Buscar la orden de venta por nombre
sale_orders = models.execute_kw(
    db, uid, password,
    'sale.order', 'search_read',
    [[['name', '=', 'S00003']]],
    {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state'], 'limit': 1}
)

if not sale_orders:
    print("❌ No se encontró la orden de venta.")
    exit()

# Mostrar datos generales de la orden
sale = sale_orders[0]
order_id = sale['id']
print("\n🧾 Orden de venta encontrada:")
print("Número:", sale['name'])
print("Cliente:", sale['partner_id'][1])
print("Total:", sale['amount_total'])
print("Estado:", sale['state'])

# Buscar líneas de venta asociadas
sale_lines = models.execute_kw(
    db, uid, password,
    'sale.order.line', 'search_read',
    [[['order_id', '=', order_id]]],
    {'fields': ['product_id', 'product_uom_qty', 'price_unit', 'name']}
)

# Mostrar detalle de productos vendidos con SKU personalizado
print("\n📦 Detalle de productos vendidos:")
for line in sale_lines:
    product_id = line['product_id'][0]

    # Obtener el SKU desde el campo personalizado x_studio_sku
    product_data = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [product_id],
        {'fields': ['x_studio_sku']}
    )

    sku = product_data[0].get('x_studio_sku', 'N/A')

    print("Producto:", line['product_id'][1])
    print("SKU:", sku)
    print("Cantidad:", line['product_uom_qty'])
    print("Precio unitario:", line['price_unit'])
    print("Descripción:", line['name'])
    print("-----")