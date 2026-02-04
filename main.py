import requests
import os
import xmlrpc.client
import logging
import psutil
import sys

from dotenv import load_dotenv
from clientes import crear_cliente_si_no_existe
from productos import buscar_producto_por_sku, buscar_ajustes_inventario, actualizar_stock_odoo_por_sku, buscar_sku_pendientes
from ventas import consultar_orden_de_venta, crear_orden_de_venta, obtener_skus_y_stock, listar_boms_con_sku_y_componentes, buscar_kits_que_contienen_componente, buscar_kits_afectados_por_componentes


# Suponiendo que ya tenés el objeto models, db, uid, password inicializados
# desde tu conexión a Odoo (ejemplo: conectar_con_reintentos())

BOM_CACHE = {}

def precargar_boms_y_probar(models, db, uid, password):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logging.info("📥 Precargando todas las BOMs desde Odoo...")

    # 1️⃣ Traer todas las BOMs
    todas_las_boms = models.execute_kw(
        db, uid, password,
        "mrp.bom", "search_read",
        [[]],
        {"fields": ["id", "product_id", "product_tmpl_id", "type"]}
    )
    logging.info(f"🔢 Total de BOMs encontradas: {len(todas_las_boms)}")

    # 2️⃣ Traer todas las líneas de BOMs
    todas_las_lineas = models.execute_kw(
        db, uid, password,
        "mrp.bom.line", "search_read",
        [[]],
        {"fields": ["bom_id", "product_id"]}
    )

    # 3️⃣ Traer todos los productos
    todos_los_productos = models.execute_kw(
        db, uid, password,
        "product.product", "search_read",
        [[]],
        {"fields": ["id", "default_code", "virtual_available", "product_tmpl_id"]}
    )

    # Diccionarios auxiliares
    productos_por_id = {p["id"]: p for p in todos_los_productos}
    lineas_por_bom = {}
    for linea in todas_las_lineas:
        bom_id = linea["bom_id"][0]
        lineas_por_bom.setdefault(bom_id, []).append(linea)

    # Construir BOM_CACHE
    for bom in todas_las_boms:
        bom_id = bom["id"]
        product_ref = bom.get("product_id")
        tmpl_ref = bom.get("product_tmpl_id")

        kit_id = None
        if product_ref:
            kit_id = product_ref[0]
        elif tmpl_ref:
            for p in todos_los_productos:
                if p["product_tmpl_id"][0] == tmpl_ref[0]:
                    kit_id = p["id"]
                    break

        if not kit_id or kit_id not in productos_por_id:
            continue

        kit_info = {
            "default_code": productos_por_id[kit_id]["default_code"],
            "virtual_available": productos_por_id[kit_id]["virtual_available"]
        }

        bom_lines = lineas_por_bom.get(bom_id, [])
        for line in bom_lines:
            comp_id = line["product_id"][0]
            comp_data = productos_por_id.get(comp_id)
            if not comp_data:
                continue
            sku_componente = comp_data["default_code"]
            BOM_CACHE.setdefault(sku_componente, []).append(kit_info)

    logging.info(f"✅ Precarga completa. BOMs procesadas: {len(todas_las_boms)}")
    logging.info(f"📦 Componentes indexados en BOM_CACHE: {len(BOM_CACHE)}")

    memoria_bytes = sys.getsizeof(BOM_CACHE)
    memoria_mb = memoria_bytes / (1024 * 1024)
    logging.info(f"💾 Memoria RAM estimada para BOM_CACHE: {memoria_mb:.2f} MB")

    # 🔄 Bucle interactivo para pruebas
    print("\n🔎 Modo prueba: escribí un SKU para ver qué kits afecta.")
    print("Escribí 'salir' para terminar.\n")

    while True:
        sku = input("👉 Ingresá un SKU: ").strip()
        if sku.lower() == "salir":
            print("👋 Saliendo del modo prueba.")
            break

        kits = BOM_CACHE.get(sku, [])
        if not kits:
            print(f"❌ El SKU '{sku}' no afecta a ningún kit.")
        else:
            print(f"✅ El SKU '{sku}' afecta a {len(kits)} kit(s):")
            for kit in kits:
                print(f"   - {kit['default_code']} (stock: {kit['virtual_available']})")



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
    print("🔟  Buscar SKU Pendientes en x_stock")
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
    elif opcion == "10":
        buscar_sku_pendientes(models, db, uid, password)

    elif opcion == "11":
        url_webhook = "https://odoo-stock-centralization-q89u.onrender.com/webhook_odoo_confirmacion"
#        url_webhook = "https://odoo-stock-centralization-q89u.onrender.com/webhook"
        
        payload = {"order_name": "S00086"}

        response = requests.post(url_webhook, json=payload)
        print(response.status_code)
        print(response.text)

    elif opcion == "12":      #Prueba de precarga de boms
        precargar_boms_y_probar(models, db, uid, password)

    elif opcion == "S":
        print("👋 ¡Hasta la próxima!")
        break
    else:
        print("❌ Opción inválida.")
