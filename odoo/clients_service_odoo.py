# 🔗 Funciones para gestionar clientes en Odoo
import logging

# Se obtiene el cliente por documento y si no se encuentra se ejecuta la función crear_cliente
# Se modifica para que no busque,sino que directamente grabe el cliente con los datos que tenga
def get_client_id_by_dni(dni=None, name=None, email=None, phone=None, shipping_data=None,
                         models=None, db=None, uid=None, password=None):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo.")
        return None

    try:
        if not dni:
            logging.warning("⚠️ DNI no definido. Se procederá a crear el cliente sin búsqueda previa.")
            nuevo_id = crear_cliente(name, email, dni, phone, shipping_data, models, db, uid, password)
            logging.info(f"✅ Cliente creado sin DNI con ID: {nuevo_id}")
            return nuevo_id

        # Buscar cliente por DNI
        partner_ids = models.execute_kw(
            db, uid, password,
            "res.partner", "search",
            [[["vat", "=", dni]]],
            {"limit": 1}
        )

        if partner_ids:
            partner_id = partner_ids[0]
            partner_data = models.execute_kw(
                db, uid, password,
                "res.partner", "read",
                [partner_ids],
                {"fields": ["name", "email", "vat"]}
            )[0]

            nombre_odoo = partner_data.get("name", "").strip().lower()
            nombre_recibido = name.strip().lower() if name else ""

            if nombre_odoo != nombre_recibido:
                logging.warning(f"⚠️ Nombre recibido ({name}) no coincide con el registrado ({partner_data['name']}). Se creará nuevo cliente.")
                nuevo_id = crear_cliente(name, email, dni, phone, shipping_data, models, db, uid, password)
                logging.info(f"✅ Cliente nuevo creado con mismo DNI pero nombre distinto: ID={nuevo_id}")
                return nuevo_id

            logging.info(f"👤 Cliente reutilizado por coincidencia de DNI y nombre: ID={partner_id}")
            return partner_id

        # Si no existe, lo creo
        nuevo_id = crear_cliente(name, email, dni, phone, shipping_data, models, db, uid, password)
        logging.info(f"✅ Cliente creado con ID: {nuevo_id}")
        return nuevo_id

    except Exception as e:
        logging.exception(f"💥 Error buscando o creando cliente con DNI {dni}: {str(e)}")
        return None


def crear_cliente(name=None, email=None, dni=None, phone=None, shipping_data=None,
                  models=None, db=None, uid=None, password=None):
    if not all([models, db, uid, password]):
        logging.error("❌ No se pudo establecer conexión con Odoo para crear cliente.")
        return None

    try:
        cliente_data = {}

        # Nombre y email
        cliente_data["name"] = name if name else "Cliente sin nombre"
        cliente_data["email"] = email if email else "cliente@pintimates.com.ar"
        cliente_data["vat"] = dni if dni else "99999999"

        # Teléfono
        if phone:
            cliente_data["phone"] = phone

        # Dirección
        if shipping_data:
            calle = shipping_data.get("address") or ""
            numero = shipping_data.get("number") or ""
            piso = shipping_data.get("floor") or ""
            cliente_data["street"] = f"{calle} {numero} {piso}".strip()

            cliente_data["street2"] = shipping_data.get("locality") or ""
            cliente_data["city"] = shipping_data.get("city") or ""
            cliente_data["zip"] = shipping_data.get("zipcode") or ""

            # Provincia: requiere ID en Odoo
            provincia_nombre = shipping_data.get("province")
            if provincia_nombre:
                state_ids = models.execute_kw(
                    db, uid, password,
                    "res.country.state", "search",
                    [[["name", "ilike", provincia_nombre]]],
                    {"limit": 1}
                )
                if state_ids:
                    cliente_data["state_id"] = state_ids[0]

        nuevo_cliente_id = models.execute_kw(
            db, uid, password,
            "res.partner", "create",
            [cliente_data]
        )

        logging.info(f"🆕 Cliente creado: ID={nuevo_cliente_id}, DNI={dni}, nombre={cliente_data['name']}")
        return nuevo_cliente_id

    except Exception as e:
        logging.exception(f"💥 Error creando cliente con DNI {dni}: {str(e)}")
        return None
