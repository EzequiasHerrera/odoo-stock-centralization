def extract_order_data(orden):
    # Datos del Cliente
    client = orden.get('customer', {})
    client_data = {
        'id': client.get('id'),
        'nombre': client.get('name'),
        'phone': client.get('phone'),
        'dni': client.get('identification'),
        'email': client.get('email'),
    }
    
    # Datos del Envío
    shipping_info = orden.get('shipping_address', {})
    shipping_data = {
        'address': shipping_info.get('address'),
        'province': shipping_info.get('province'),
        'city': shipping_info.get('city'),
        'locality': shipping_info.get('locality'),
        'floor': shipping_info.get('floor'),
        'number': shipping_info.get('number'),
        'zipcode': shipping_info.get('zipcode')
    }
    
    # Detalles de la Venta
    products = []
    for prod in orden.get('products', []):
        products.append({
            'product_id': prod.get('product_id'),
            'name': prod.get('name_without_variants'),
            'sku': prod.get('sku'),
            'quantity': prod.get('quantity'),
            'price': prod.get('price'),
        })
    
    # Retornar objeto unificado
    return {
        'datos_cliente': client_data,
        'datos_envio': shipping_data,
        'detalles_venta': products
    }