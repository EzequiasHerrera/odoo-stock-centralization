# 🔗 Funciones para gestionar clientes en Odoo
import logging

# Se obtiene el cliente por documento y si no se encuentra se ejecuta la función crear_cliente
def get_client_id_by_dni(dni, name=None, email=None, models=None, db=None, uid=None, password=None):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo.")
        return None

    try:
        # Busco cliente por DNI
        partner_id = models.execute_kw(
            db, uid, password,
            "res.partner", "search",
            [[["vat", "=", dni]]],
            {"limit": 1}
        )

        if partner_id:
            logging.info(f"👤 Cliente encontrado por DNI {dni}: ID={partner_id[0]}")
            return partner_id[0]

        # Si no existe, lo creo
        nuevo_id = crear_cliente(name, email, dni, models, db, uid, password)
        logging.info(f"✅ Cliente creado con ID: {nuevo_id}")
        return nuevo_id

    except Exception as e:
        logging.exception(f"💥 Error buscando o creando cliente con DNI {dni}: {str(e)}")
        return None


def crear_cliente(name, email, dni, models=None, db=None, uid=None, password=None):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para crear cliente.")
        return None

    try:
        nuevo_cliente_id = models.execute_kw(
            db, uid, password,
            "res.partner", "create",
            [{"name": name, "email": email, "vat": dni}]
        )
        logging.info(f"🆕 Cliente creado: ID={nuevo_cliente_id}, DNI={dni}, nombre={name}")
        return nuevo_cliente_id

    except Exception as e:
        logging.exception(f"💥 Error creando cliente con DNI {dni}: {str(e)}")
        return None
