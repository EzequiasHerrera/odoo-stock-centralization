import os
import xmlrpc.client
from dotenv import load_dotenv

def connect_odoo():
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
        print("❌ Error al conectar. Verificá los datos.")
        return None, None, None, None

    print("✅ Conectado correctamente - odoo.connect_odoo")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", transport=transport)

    return models, db, uid, password