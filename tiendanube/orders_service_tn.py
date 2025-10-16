def extraer_datos_orden(orden):
    # Datos del Cliente
    cliente = orden.get('customer', {})
    datos_cliente = {
        'id': cliente.get('id'),
        'nombre': cliente.get('name'),
        'email': cliente.get('email'),
        'telefono': cliente.get('phone'),
        'identificacion': cliente.get('identification'),
        'total_gastado': cliente.get('total_spent'),
        'moneda': cliente.get('total_spent_currency'),
        'cliente_activo': cliente.get('active'),
        'acepta_marketing': cliente.get('accepts_marketing')
    }
    
    # Datos del Envío
    direccion_envio = orden.get('shipping_address', {})
    datos_envio = {
        'nombre_destinatario': direccion_envio.get('name'),
        'direccion': direccion_envio.get('address'),
        'numero': direccion_envio.get('number'),
        'piso': direccion_envio.get('floor'),
        'localidad': direccion_envio.get('locality'),
        'ciudad': direccion_envio.get('city'),
        'provincia': direccion_envio.get('province'),
        'codigo_postal': direccion_envio.get('zipcode'),
        'pais': direccion_envio.get('country'),
        'telefono': direccion_envio.get('phone'),
        'metodo_envio': orden.get('shipping'),
        'opcion_envio': orden.get('shipping_option'),
        'costo_envio_cliente': orden.get('shipping_cost_customer'),
        'costo_envio_propietario': orden.get('shipping_cost_owner'),
        'numero_seguimiento': orden.get('shipping_tracking_number'),
        'url_seguimiento': orden.get('shipping_tracking_url'),
        'estado_envio': orden.get('shipping_status'),
        'enviado_en': orden.get('shipped_at')
    }
    
    # Detalles de la Venta
    productos = []
    for prod in orden.get('products', []):
        productos.append({
            'id': prod.get('id'),
            'nombre': prod.get('name'),
            'sku': prod.get('sku'),
            'cantidad': prod.get('quantity'),
            'precio': prod.get('price'),
            'precio_comparacion': prod.get('compare_at_price'),
            'peso': prod.get('weight'),
            'imagen': prod.get('image', {}).get('src')
        })
    
    detalles_pago = orden.get('payment_details', {})
    
    detalles_venta = {
        'numero_orden': orden.get('number'),
        'id_orden': orden.get('id'),
        'token': orden.get('token'),
        'subtotal': orden.get('subtotal'),
        'descuento': orden.get('discount'),
        'descuento_cupon': orden.get('discount_coupon'),
        'total': orden.get('total'),
        'total_usd': orden.get('total_usd'),
        'moneda': orden.get('currency'),
        'estado_pago': orden.get('payment_status'),
        'total_pagado': orden.get('total_paid'),
        'pagado_en': orden.get('paid_at'),
        'metodo_pago': detalles_pago.get('method'),
        'tarjeta': detalles_pago.get('credit_card_company'),
        'cuotas': detalles_pago.get('installments'),
        'gateway': orden.get('gateway_name'),
        'productos': productos,
        'cantidad_productos': len(productos),
        'peso_total': orden.get('weight'),
        'estado_orden': orden.get('status'),
        'proxima_accion': orden.get('next_action'),
        'creado_en': orden.get('created_at'),
        'actualizado_en': orden.get('updated_at'),
        'completado_en': orden.get('completed_at', {}).get('date') if isinstance(orden.get('completed_at'), dict) else orden.get('completed_at'),
        'nota': orden.get('note'),
        'nota_propietario': orden.get('owner_note')
    }
    
    return {
        'datos_cliente': datos_cliente,
        'datos_envio': datos_envio,
        'detalles_venta': detalles_venta
    }

# Ejemplo de uso
if __name__ == "__main__":
    import json
    
    resultado = extraer_datos_orden(orden)
    
    print("=== DATOS DEL CLIENTE ===")
    print(json.dumps(resultado['datos_cliente'], indent=2, ensure_ascii=False))
    
    print("\n=== DATOS DEL ENVÍO ===")
    print(json.dumps(resultado['datos_envio'], indent=2, ensure_ascii=False))
    
    print("\n=== DETALLES DE LA VENTA ===")
    print(json.dumps(resultado['detalles_venta'], indent=2, ensure_ascii=False))