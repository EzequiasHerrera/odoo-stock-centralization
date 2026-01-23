import pandas as pd
import sys
import os
import chardet
import csv

def detectar_encoding(archivo):
    with open(archivo, 'rb') as f:
        resultado = chardet.detect(f.read(10000))
    return resultado['encoding']

def detectar_delimitador(archivo, encoding_detectado):
    with open(archivo, 'r', encoding=encoding_detectado, errors='ignore') as f:
        muestra = f.read(2048)
        dialecto = csv.Sniffer().sniff(muestra)
    return dialecto.delimiter

def generar_borrar_csv(archivo_tiendanube, archivo_odoo, archivo_salida):
    # Detectar encoding y delimitador del archivo de Tiendanube
    encoding_tn = detectar_encoding(archivo_tiendanube)
    delimitador_tn = detectar_delimitador(archivo_tiendanube, encoding_tn)

    print(f"Tiendanube -> encoding: {encoding_tn}, delimitador: '{delimitador_tn}'")

    # Leer Tiendanube limpio
    df_tn = pd.read_csv(archivo_tiendanube, sep=delimitador_tn, encoding=encoding_tn)

    # Leer Odoo.xlsx
    df_odoo = pd.read_excel(archivo_odoo)

    # Normalizar nombres de columnas
    df_tn.columns = df_tn.columns.str.strip()
    df_odoo.columns = df_odoo.columns.str.strip()

    # Extraer SKUs de Tiendanube (columna I = índice 8)
    skus_tn = df_tn.iloc[:, 8].astype(str).str.strip()

    # Extraer referencias internas de Odoo (columna F = índice 5)
    referencias_odoo = df_odoo.iloc[:, 5].astype(str).str.strip()

    # Filtrar productos de Odoo cuyo SKU no esté en Tiendanube
    df_borrar = df_odoo[~referencias_odoo.isin(skus_tn)]

    # Guardar resultado en borrar.csv con separador ; y encoding de Tiendanube
    df_borrar.to_csv(archivo_salida, index=False, sep=delimitador_tn, encoding=encoding_tn)
    print(f"Archivo generado: {archivo_salida} con {len(df_borrar)} productos para borrar")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python Borrar.py tiendanube_limpio.csv Odoo.xlsx")
    else:
        archivo_tiendanube = sys.argv[1]
        archivo_odoo = sys.argv[2]
        archivo_salida = "borrar.csv"
        generar_borrar_csv(archivo_tiendanube, archivo_odoo, archivo_salida)
