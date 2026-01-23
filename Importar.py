import pandas as pd
import sys
import os
import chardet
import csv

# ------ COMPARA EL EXPORTADO DE ODOO (COMPARARTN) CON EL DE TN PARA IDENTIFICAR FALTANTES DE ODOO ----- #

def detectar_encoding(archivo):
    with open(archivo, 'rb') as f:
        resultado = chardet.detect(f.read(10000))
    return resultado['encoding']

def detectar_delimitador(archivo, encoding_detectado):
    with open(archivo, 'r', encoding=encoding_detectado, errors='ignore') as f:
        muestra = f.read(2048)
        dialecto = csv.Sniffer().sniff(muestra)
    return dialecto.delimiter

def generar_importar_csv(archivo_tiendanube, archivo_odoo, archivo_salida):
    # Detectar encoding y delimitador del archivo de Tiendanube
    encoding_tn = detectar_encoding(archivo_tiendanube)
    delimitador_tn = detectar_delimitador(archivo_tiendanube, encoding_tn)

    print(f"Tiendanube -> encoding: {encoding_tn}, delimitador: '{delimitador_tn}'")

    # Leer Tiendanube limpio
    df_tn = pd.read_csv(archivo_tiendanube, sep=delimitador_tn, encoding=encoding_tn)

    # Leer Odoo.xlsx (usa openpyxl por defecto)
    df_odoo = pd.read_excel(archivo_odoo)

    # Normalizar nombres de columnas
    df_tn.columns = df_tn.columns.str.strip()
    df_odoo.columns = df_odoo.columns.str.strip()

    # Extraer SKUs de Tiendanube (columna I)
    skus_tn = df_tn.iloc[:, 8].astype(str).str.strip()  # Columna I = índice 8

    # Extraer referencias internas de Odoo (columna F)
    referencias_odoo = df_odoo.iloc[:, 5].astype(str).str.strip()  # Columna F = índice 5

    # Filtrar productos cuyo SKU no esté en Odoo
    df_faltantes = df_tn[~skus_tn.isin(referencias_odoo)]

    # Guardar resultado en importar.csv con separador ; y mismo encoding que Tiendanube
    df_faltantes.to_csv(archivo_salida, index=False, sep=delimitador_tn, encoding=encoding_tn)
    print(f"Archivo generado: {archivo_salida} con {len(df_faltantes)} productos faltantes")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python Importar.py tiendanube_limpio.csv Odoo.xlsx")
    else:
        archivo_tiendanube = sys.argv[1]
        archivo_odoo = sys.argv[2]
        archivo_salida = "importar.csv"
        generar_importar_csv(archivo_tiendanube, archivo_odoo, archivo_salida)
