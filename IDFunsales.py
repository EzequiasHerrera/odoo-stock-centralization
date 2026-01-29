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

def extraer_info(fila, pos):
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
        return None, [], []

    # Separar nombre y propiedades usando el último "-"
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

    return producto, propiedades, valores

def buscar_sku_real(df, producto, propiedades, valores):
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
        sku_real = str(coincidencias_real.iloc[0,8]).strip()
    else:
        sku_real = "NO_ENCONTRADO"

    # Si empieza con "Comb", eliminar el primer módulo hasta el primer "-"
    if sku_real.startswith("Comb"):
        if "-" in sku_real:
            sku_sin_comb = sku_real.split("-", 1)[1]
        else:
            sku_sin_comb = ""
    else:
        sku_sin_comb = ""

    return sku_real, sku_sin_comb

def procesar_archivo(archivo_csv, archivo_salida):
    # Detectar encoding y delimitador
    encoding_tn = detectar_encoding(archivo_csv)
    delimitador_tn = detectar_delimitador(archivo_csv, encoding_tn)

    print(f"Detectado encoding: {encoding_tn}, delimitador: '{delimitador_tn}'")

    # Leer CSV completo
    df = pd.read_csv(archivo_csv, sep=delimitador_tn, encoding=encoding_tn)

    # Extraer todos los IDs únicos de FunSales
    ids_funsales = set()
    contador = 0
    for sku in df.iloc[:,8].astype(str):
        if "|" in sku:
            for x in sku.split("|"):
                if x.isdigit():
                    if x not in ids_funsales:
                        ids_funsales.add(x)
                        contador += 1
                        if contador % 10 == 0:
                            print(f"IDs encontrados hasta ahora: {contador}")

    ids_funsales = sorted(ids_funsales)
    print(f"Se encontraron {len(ids_funsales)} IDs únicos de FunSales.")

    resultados = []

    for i, fun_id in enumerate(ids_funsales, start=1):
        coincidencias = df[df.iloc[:,8].astype(str).str.contains(fun_id)]
        if coincidencias.empty:
            continue

        fila = coincidencias.iloc[0]
        sku_funsales = str(fila.iloc[8]).strip()
        ids = [x for x in sku_funsales.split("|") if x.isdigit()]
        if fun_id not in ids:
            continue
        pos = ids.index(fun_id)

        producto, propiedades, valores = extraer_info(fila, pos)
        if producto is None:
            continue

        sku_real, sku_sin_comb = buscar_sku_real(df, producto, propiedades, valores)

        resultados.append({
            "ID_Funsales": fun_id,
            "Producto": producto,
            "Propiedad_1": propiedades[0],
            "Valor_1": valores[0],
            "Propiedad_2": propiedades[1],
            "Valor_2": valores[1],
            "Propiedad_3": propiedades[2],
            "Valor_3": valores[2],
            "SKU_real": sku_real,
            "SKU_sin_Comb": sku_sin_comb
        })

        # Mostrar progreso cada 10 IDs procesados
        if i % 10 == 0:
            print(f"Procesados {i} IDs...")

        # Cada 500 IDs preguntar si continuar
        if i % 500 == 0:
            respuesta = input(f"Ya se procesaron {i} IDs. ¿Desea continuar? (s/n): ").strip().lower()
            if respuesta != "s":
                break

    # Guardar resultados en Excel
    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_excel(archivo_salida, index=False)
    print(f"Archivo generado: {archivo_salida} con {len(df_resultados)} registros procesados.")

if __name__ == "__main__":
    archivo_csv = input("Ingrese el nombre del archivo CSV (ej: tiendanube_limpio.csv): ").strip()
    archivo_salida = "resultado_funsales.xlsx"
    procesar_archivo(archivo_csv, archivo_salida)
