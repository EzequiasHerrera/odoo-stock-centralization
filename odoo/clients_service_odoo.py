#Separamos la lógica, se obtiene el cliente por documento y si no se encuentra se ejecuta la funcion crear_cliente
def get_client_id_by_dni(models, db, uid, password, documento, nombre=None, email=None):
    #Obtengo ID de 
    partner_id = models.execute_kw(
        db, uid, password,
        'res.partner', 'search',
        [[['vat', '=', documento]]],
        {'limit': 1}
    )

    if partner_id:
        return partner_id[0]

    if not nombre or not email:
        print("⚠️ Cliente no encontrado y faltan datos para crearlo.")
        #Aquí se adaptaría con datos de TN
        nombre = input("📧 Ingresá el Nombre del cliente: ")
        email = input("📧 Ingresá el email del cliente: ")

    nuevo_id = crear_cliente(models, db, uid, password, nombre, email, documento)
    print(f"✅ Cliente creado con ID: {nuevo_id}")
    return nuevo_id

def crear_cliente(models, db, uid, password, nombre, email, documento):
    nuevo_cliente_id = models.execute_kw(
        db, uid, password,
        'res.partner', 'create',
        [{
            'name': nombre,
            'email': email,
            'vat': documento
        }]
    )
    return nuevo_cliente_id