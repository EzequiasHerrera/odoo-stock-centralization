# Función auxiliar para crear cliente si no existe
def crear_cliente_si_no_existe(models, db, uid, password, documento):
    # Buscar cliente por Documento exacto
    partner_ids = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[['vat', '=', documento]]],
        {'limit': 1}
    )

    # Buscar cliente por nombre exacto
#    partner_ids = models.execute_kw(
#        db, uid, password,
#        'res.partner', 'search',
#        [[['name', '=', nombre]]],
#        {'limit': 1}
#    )

    # Si no existe, crear el cliente
    if not partner_ids:
        print("⚠️ Cliente no encontrado. Vamos a crearlo.")
        nombre = input("📧 Ingresá el Nombre del cliente: ")
        email = input("📧 Ingresá el email del cliente: ")
        documento = input("🪪 Ingresá el número de documento (DNI/CUIT): ")

        nuevo_cliente_id = models.execute_kw(
            db, uid, password,
            'res.partner', 'create',
            [{
                'name': nombre,
                'email': email,
                'vat': documento
            }]
        )
        print(f"✅ Cliente creado con ID: {nuevo_cliente_id}")
        return nuevo_cliente_id

    return partner_ids[0]