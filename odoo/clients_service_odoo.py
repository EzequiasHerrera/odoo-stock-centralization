# CONECTO CON ODOO
from odoo.connect_odoo import connect_odoo
models, db, uid, password = connect_odoo()

# Separamos la lógica, se obtiene el cliente por documento y si no se encuentra se ejecuta la funcion crear_cliente
def get_client_id_by_dni(dni, name=None, email=None):
    # Obtengo ID de cliente
    partner_id = models.execute_kw(
        db, uid, password, "res.partner", "search", [[["vat", "=", dni]]], {"limit": 1}
    )

    if partner_id:
        return partner_id[0]

    nuevo_id = crear_cliente(name, email, dni)
    print(f"✅ Cliente creado con ID: {nuevo_id}")
    return nuevo_id


def crear_cliente(name, email, dni):
    nuevo_cliente_id = models.execute_kw(
        db,
        uid,
        password,
        "res.partner",
        "create",
        [{"name": name, "email": email, "vat": dni}],
    )
    return nuevo_cliente_id
