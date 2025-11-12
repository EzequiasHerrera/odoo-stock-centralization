import os
import xmlrpc.client
import logging
import time

def connect_odoo():

    # Para funcionamiento local -------------------------------------------
    if os.getenv("RENDER") is None:
        logging.info("✅ Ejecución LOCAL - Cargando variables...")
        from dotenv import load_dotenv
        load_dotenv()

    # ✅ Validar variables de entorno
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASS")

    if not all([url, db, username, password]):
        logging.error("❌ Faltan variables de entorno para conectar a Odoo")
        return None, None, None, None

    try:
        class SafeTransport(xmlrpc.client.SafeTransport):
            def __init__(self, use_datetime=False):
                super().__init__(use_datetime=use_datetime)

        transport = SafeTransport()
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", transport=transport)

        uid = common.authenticate(db, username, password, {})
        if not uid:
            logging.error("❌ Falló la autenticación con Odoo. Verificá credenciales.")
            return None, None, None, None

        models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", transport=transport)
        logging.info("✅ Conexión exitosa con Odoo")
        return models, db, uid, password

    except Exception as e:
        logging.exception(f"💥 Error al conectar con Odoo: {str(e)}")
        return None, None, None, None


def conectar_con_reintentos(max_reintentos=5, espera_segundos=10):
    for intento in range(1, max_reintentos + 1):
        logging.info(f"🔄 Intento {intento} de conexión a Odoo...")
        models, db, uid, password = connect_odoo()
        if all([models, db, uid, password]):
            return models, db, uid, password
        else:
            logging.warning("⚠️ Falló la conexión. Reintentando...")
            time.sleep(espera_segundos)
    logging.error("❌ No se pudo conectar a Odoo tras múltiples intentos")
    return None, None, None, None