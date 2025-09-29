import os
import xmlrpc.client
from dotenv import load_dotenv

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

# Función 1: Buscar producto por SKU
def buscar_producto_por_sku():
    sku = input("🔍 Ingresá el SKU del producto: ")
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[['x_studio_sku', '=', sku]]],
        {'limit': 1}
    )

    if product_ids:
        product = models.execute_kw(
            db, uid, password,
            'product.product', 'read',
            [product_ids],
            {'fields': ['name', 'x_studio_color', 'x_studio_talle', 'qty_available', 'virtual_available']}
        )
        print("\n📦 Producto encontrado:")
        print("Nombre:", product[0]['name'])
        print("Color:", product[0].get('x_studio_color', 'N/A'))
        print("Talle:", product[0].get('x_studio_talle', 'N/A'))
        print("Stock disponible:", product[0]['qty_available'])
        print("Stock virtual:", product[0]['virtual_available'])
    else:
        print("❌ Producto no encontrado.")

# Función 2: Consultar orden de venta por nombre
def consultar_orden_de_venta():
    orden = input("🧾 Ingresá el nombre de la orden de venta (ej. S00003): ")
    sale_orders = models.execute_kw(
        db, uid, password,
        'sale.order', 'search_read',
        [[['name', '=', orden]]],
        {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state'], 'limit': 1}
    )

    if not sale_orders:
        print("❌ No se encontró la orden de venta.")
        return

    sale = sale_orders[0]
    order_id = sale['id']
    print("\n🧾 Orden de venta encontrada:")
    print("Número:", sale['name'])
    print("Cliente:", sale['partner_id'][1])
    print("Total:", sale['amount_total'])
    print("Estado:", sale['state'])

    # Buscar líneas de venta
    sale_lines = models.execute_kw(
        db, uid, password,
        'sale.order.line', 'search_read',
        [[['order_id', '=', order_id]]],
        {'fields': ['product_id', 'product_uom_qty', 'price_unit', 'name']}
    )

    print("\n📦 Detalle de productos vendidos:")
    for line in sale_lines:
        product_id = line['product_id'][0]
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

# Función 3: Crear una orden de venta con dos productos
def crear_orden_de_venta():
    cliente = input("👤 Ingresá el nombre del cliente: ")

    # Buscar cliente por nombre exacto
    partner_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[['name', '=', cliente]]],
        {'limit': 1}
    )

    # Si no existe, crear el cliente
    if not partner_ids:
        print("⚠️ Cliente no encontrado. Vamos a crearlo.")
        email = input("📧 Ingresá el email del cliente: ")
        documento = input("🪪 Ingresá el número de documento (DNI/CUIT): ")

        nuevo_cliente_id = models.execute_kw(
            db, uid, password,
            'res.partner', 'create',
            [{
                'name': cliente,
                'email': email,
                'vat': documento
            }]
        )
        print(f"✅ Cliente creado con ID: {nuevo_cliente_id}")
        partner_ids = [nuevo_cliente_id]

    # Crear la orden de venta
    order_id = models.execute_kw(
        db, uid, password,
        'sale.order', 'create',
        [{
            'partner_id': partner_ids[0],
            'date_order': '2025-09-29',
        }]
    )

    print(f"\n🛒 Orden creada con ID: {order_id}")

    # Ingresar dos SKUs
    for i in range(1, 3):
        sku = input(f"🔢 Ingresá el SKU del producto {i}: ")
        product_ids = models.execute_kw(
            db, uid, password,
            'product.product', 'search',
            [[['x_studio_sku', '=', sku]]],
            {'limit': 1}
        )

        if not product_ids:
            print(f"❌ Producto {i} no encontrado.")
            continue

        cantidad = float(input(f"📦 Cantidad del producto {i}: "))
        precio = float(input(f"💲 Precio unitario del producto {i}: "))

        # Crear línea de venta
        models.execute_kw(
            db, uid, password,
            'sale.order.line', 'create',
            [{
                'order_id': order_id,
                'product_id': product_ids[0],
                'product_uom_qty': cantidad,
                'price_unit': precio,
                'name': f"Producto {i} - SKU {sku}",
            }]
        )

    # Confirmar la orden para que impacte en el stock
    models.execute_kw(
        db, uid, password,
        'sale.order', 'action_confirm',
        [[order_id]]
    )

    print("✅ Orden confirmada y stock actualizado.")

# Menú interactivo
print("\n🧪 ¿Qué querés testear?")
print("1️⃣ Buscar producto por SKU")
print("2️⃣ Consultar orden de venta por nombre")
print("3️⃣ Crear una orden de venta con dos productos")

opcion = input("👉 Ingresá el número de opción (1, 2 o 3): ")

if opcion == "1":
    buscar_producto_por_sku()
elif opcion == "2":
    consultar_orden_de_venta()
elif opcion == "3":
    crear_orden_de_venta()
else:
    print("❌ Opción inválida.")
