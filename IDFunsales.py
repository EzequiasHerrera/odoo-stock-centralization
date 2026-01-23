import pandas as pd
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

def buscar_identidad(archivo_tiendanube, fun_id):
    # Detectar encoding y delimitador
    encoding_tn = detectar_encoding(archivo_tiendanube)
    delimitador_tn = detectar_delimitador(archivo_tiendanube, encoding_tn)

    print(f"Detectado encoding: {encoding_tn}, delimitador: '{delimitador_tn}'")

    # Leer CSV completo
    df = pd.read_csv(archivo_tiendanube, sep=delimitador_tn, encoding=encoding_tn)

    # Buscar filas donde la columna I contenga el ID
    coincidencias = df[df.iloc[:,8].astype(str).str.contains(fun_id)]

    if coincidencias.empty:
        print(f"No se encontró el ID {fun_id} en el archivo.")
        return

    # Tomar la primera coincidencia
    fila = coincidencias.iloc[0]
    sku_funsales = str(fila.iloc[8]).strip()

    # Determinar posición del ID dentro del SKU
    ids = [x for x in sku_funsales.split("|") if x.isdigit()]
    if fun_id not in ids:
        print(f"El ID {fun_id} no está en el SKU {sku_funsales}")
        return
    pos = ids.index(fun_id)

    # Extraer descripción y valores según posición
    if pos == 0:
        desc = str(fila.iloc[1]).strip()  # Columna B
        vals = str(fila.iloc[2]).strip()  # Columna C
    elif pos == 1:
        desc = str(fila.iloc[3]).strip()  # Columna D
        vals = str(fila.iloc[4]).strip()  # Columna E
    elif pos == 2:
        desc = str(fila.iloc[5]).strip()  # Columna F
        vals = str(fila.iloc[6]).strip()  # Columna G
    else:
        print("Posición de ID no soportada.")
        return

    # Separar nombre y propiedades usando el ÚLTIMO "-"
    if " - " in desc:
        producto, props_str = desc.rsplit(" - ", 1)
        propiedades = props_str.split(" + ")
    else:
        producto = desc
        propiedades = []

    valores = vals.split(" + ")

    # Normalizar a 3 propiedades
    while len(propiedades) < 3:
        propiedades.append("")
    while len(valores) < 3:
        valores.append("")

    # Construir filtro dinámico
    filtro = (df.iloc[:,0].astype(str).str.strip() == producto)

    if propiedades[0]:
        filtro &= (df.iloc[:,1].astype(str).str.strip() == propiedades[0])
        filtro &= (df.iloc[:,2].astype(str).str.strip() == valores[0])

    if propiedades[1]:
        filtro &= (df.iloc[:,3].astype(str).str.strip() == propiedades[1])
        filtro &= (df.iloc[:,4].astype(str).str.strip() == valores[1])

    if propiedades[2]:
        filtro &= (df.iloc[:,5].astype(str).str.strip() == propiedades[2])
        filtro &= (df.iloc[:,6].astype(str).str.strip() == valores[2])

    coincidencias_real = df[filtro]

    if not coincidencias_real.empty:
        sku_real = coincidencias_real.iloc[0,8]
    else:
        sku_real = "NO_ENCONTRADO"

    print("\nResultado:")
    print(f"ID_Funsales: {fun_id}")
    print(f"Producto: {producto}")
    print(f"Propiedad_1: {propiedades[0]} -> {valores[0]}")
    print(f"Propiedad_2: {propiedades[1]} -> {valores[1]}")
    print(f"Propiedad_3: {propiedades[2]} -> {valores[2]}")
    print(f"SKU_real: {sku_real}")

if __name__ == "__main__":
    archivo_tiendanube = "tiendanube_limpio.csv"
    fun_id = input("Ingrese el ID numérico de FunSales: ").strip()
    buscar_identidad(archivo_tiendanube, fun_id)
