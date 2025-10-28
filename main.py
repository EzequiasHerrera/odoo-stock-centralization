import os
import xmlrpc.client
from dotenv import load_dotenv
from clientes import crear_cliente_si_no_existe
from productos import buscar_producto_por_sku, buscar_ajustes_inventario, actualizar_stock_odoo_por_sku
from ventas import consultar_orden_de_venta, crear_orden_de_venta, obtener_skus_y_stock, listar_boms_con_sku_y_componentes, buscar_kits_que_contienen_componente, buscar_kits_afectados_por_componentes

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
    print("1️⃣  Buscar producto por SKU")
    print("2️⃣  Consultar orden de venta por nombre")
    print("3️⃣  Crear una orden de venta con tres productos")
    print("4️⃣  Obtener SKUs y stock desde una orden de venta")
    print("5️⃣  Mostrar Listas de Materiales de kits")
    print("6️⃣  Buscar kits que contienen un SKU como componente")
    print("7️⃣  Buscar SKUs afectados por una venta")
    print("8️⃣  Buscar Cambios de Inventario")
    print("9️⃣  Cargar stock en Odoo por SKU")
    print("🔟  ")
    print("S Salir del programa")

    opcion = input("👉 Ingresá el número de opción: ")

    if opcion == "1":
        sku = input("SKU: ")
        producto = buscar_producto_por_sku(models, db, uid, password, sku)

        if producto:
            print(f"🔎 Producto: {producto['name']} (SKU: {producto['sku']})")
            print(f"   Color: {producto['color']}")
            print(f"   Talle: {producto['talle']}")
            print(f"   Stock disponible: {producto['stock_disponible']}")
            print(f"   Stock virtual: {producto['stock_virtual']}")

            if producto['bom']:
                print("📦 Componentes del kit:")
                for comp in producto['bom']:
                    print(f"   - {comp['nombre']} (SKU: {comp['sku']})")
                    print(f"     Cantidad en kit: {comp['cantidad_en_kit']}")
                    print(f"     Stock disponible: {comp['stock_disponible']}")
                    print(f"     Stock virtual: {comp['stock_virtual']}")
        else:
            print("❌ No se encontró el producto.")
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
    elif opcion == "5":
        kits = listar_boms_con_sku_y_componentes(models, db, uid, password)
        if kits:
            print("\n📋 Listado de kits y sus componentes:")
            for k in kits:
                print(f"\n🔹 Kit: {k['kit_name']} (SKU: {k['kit_sku']}) | Tipo: {k['tipo_bom']}")
                for comp in k['componentes']:
                    print(f"   - {comp['nombre']} (SKU: {comp['sku']}) | Cantidad: {comp['cantidad']}")
        else:
            print("📭 No se encontraron listas de materiales con productos asociados.")
    elif opcion == "6":
        sku_comp = input("SKU: ")
        kits = buscar_kits_que_contienen_componente(models, db, uid, password, sku_comp)
        print("\n📋 Kits que contienen el SKU como componente:")
        for sku in kits:
            print(f"   - {sku}")        
    elif opcion == "7":
        nombre_orden = input("🧾 Ingresá el nombre de la orden de venta (ej. S00003): ")
        productos_afectados = obtener_skus_y_stock(models, db, uid, password, nombre_orden)
        skus_componentes = [p["default_code"] for p in productos_afectados]

        kits_afectados = buscar_kits_afectados_por_componentes(models, db, uid, password, skus_componentes)

        # Unificar ambas listas
        todos_los_skus = productos_afectados + kits_afectados

        # Deduplicar por SKU
        skus_unicos = {}
        for item in todos_los_skus:
            sku = item.get("default_code", "N/A")
            # Si el SKU ya está en el diccionario, lo ignoramos
            if sku not in skus_unicos:
                skus_unicos[sku] = item

        # Convertir de nuevo a lista
        lista_final_sin_duplicados = list(skus_unicos.values())

        print("\n📦 Lista final de SKUs a actualizar en TiendaNube:")
        for producto in lista_final_sin_duplicados:
            sku = producto.get("default_code", "N/A")
            stock = producto.get("virtual_available", 0.0)
            print(f"   ➤ SKU: {sku} | Stock virtual: {stock}")

    elif opcion == "8":
        inventarios = buscar_ajustes_inventario(models, db, uid, password)
    elif opcion == "9":
        sku = input("SKU: ")
        nueva_cantidad = input("NUEVA CANTIDAD: ")
        actualizar_stock_odoo_por_sku(models, db, uid, password, sku, nueva_cantidad)

    elif opcion == "S":
        print("👋 ¡Hasta la próxima!")
        break
    else:
        print("❌ Opción inválida.")
