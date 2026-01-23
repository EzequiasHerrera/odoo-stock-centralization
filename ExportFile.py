import pandas as pd
import sys
import os
import chardet
import csv

# ------ PERMITE LIMPIAR EL CSV EXPORTADO DE TIENDANUBE ----- #

def detectar_encoding(archivo):
    with open(archivo, 'rb') as f:
        resultado = chardet.detect(f.read(10000))
    return resultado['encoding']

def detectar_delimitador(archivo, encoding_detectado):
    with open(archivo, 'r', encoding=encoding_detectado, errors='ignore') as f:
        muestra = f.read(2048)
        dialecto = csv.Sniffer().sniff(muestra)
    return dialecto.delimiter

def procesar_csv(archivo_entrada, archivo_salida):
    encoding_detectado = detectar_encoding(archivo_entrada)
    delimitador = detectar_delimitador(archivo_entrada, encoding_detectado)

    print(f"Detectado encoding: {encoding_detectado}, delimitador: '{delimitador}'")

    df = pd.read_csv(archivo_entrada, sep=delimitador, encoding=encoding_detectado)

    # ✅ Propagar valores de la columna B en toda la columna
    df.iloc[:, 1] = df.iloc[:, 1].fillna(method="ffill")

    # Eliminar columnas específicas
    columnas_a_borrar = [0, 2, 3, 5, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21]
    columnas_a_borrar.extend(list(range(24, 40)))
    df = df.drop(df.columns[columnas_a_borrar], axis=1)

    # Guardar archivo limpio con mismo separador y encoding que el original
    df.to_csv(archivo_salida, index=False, encoding=encoding_detectado, sep=delimitador)
    print(f"Archivo procesado y guardado en: {archivo_salida}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ExportFile.py archivo.csv")
    else:
        archivo_entrada = sys.argv[1]
        nombre_salida = os.path.splitext(archivo_entrada)[0] + "_limpio.csv"
        procesar_csv(archivo_entrada, nombre_salida)
