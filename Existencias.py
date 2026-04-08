import pandas as pd
import os
import chardet
import csv
from datetime import datetime

# ------ EXISTENCIAS.PY: Genera Excel con hojas Productos, Filtrados y Artículos ----- #

def detectar_encoding(archivo):
    with open(archivo, 'rb') as f:
        resultado = chardet.detect(f.read(10000))
    return resultado['encoding']

def detectar_delimitador(archivo, encoding_detectado):
    with open(archivo, 'r', encoding=encoding_detectado, errors='ignore') as f:
        muestra = f.read(2048)
        dialecto = csv.Sniffer().sniff(muestra)
    return dialecto.delimiter

def procesar_csv():
    archivo_entrada = "tiendanube.csv"
    if not os.path.exists(archivo_entrada):
        print(f"No se encontró el archivo {archivo_entrada}")
        return

    encoding_detectado = detectar_encoding(archivo_entrada)
    delimitador = detectar_delimitador(archivo_entrada, encoding_detectado)

    print(f"Detectado encoding: {encoding_detectado}, delimitador: '{delimitador}'")

    df = pd.read_csv(archivo_entrada, sep=delimitador, encoding=encoding_detectado, low_memory=False)

    # --- Selección de columnas específicas ---
    columnas_indices = [1, 3, 4, 6, 8, 10, 12, 14, 16, 17, 22, 23]
    df = df.iloc[:, columnas_indices]

    # ✅ Propagar valores en columnas "Nombre" y "Categorías"
    df.iloc[:, 0] = df.iloc[:, 0].ffill()  # Nombre
    df.iloc[:, 1] = df.iloc[:, 1].ffill()  # Categorías

    # --- Construir hoja Filtrados ---
    columna_sku = df.columns[11]   # SKU (columna L en Productos)
    columna_nombre = df.columns[0] # Nombre (columna A en Productos)

    mask_pipe = df[columna_sku].astype(str).str.contains(r"\|", regex=True)
    mask_comb = df[columna_sku].astype(str).str.startswith("Comb")
    mask_box = df[columna_nombre].astype(str).str.contains("Box", case=False, na=False)

    df_filtrados = df[~(mask_pipe | mask_comb | mask_box)]

    # --- Construir hoja Artículos ---
    nombre_col = df_filtrados.columns[0]       # Nombre
    categoria_col = df_filtrados.columns[1]    # Categoría
    precio_col = df_filtrados.columns[8]       # Precio
    precio_promo_col = df_filtrados.columns[9] # Precio Promocional
    stock_col = df_filtrados.columns[10]       # Stock

    # Agrupar por Nombre y Categoría
    df_articulos = (
        df_filtrados
        .groupby([nombre_col, categoria_col], as_index=False)
        .agg({
            stock_col: "sum",
            precio_col: "first",
            precio_promo_col: "first"
        })
    )

    # ✅ Nueva columna: Valor Comercial (Stock * Precio Promocional)
    df_articulos[stock_col] = pd.to_numeric(df_articulos[stock_col], errors="coerce")

    df_articulos[precio_promo_col] = (
        df_articulos[precio_promo_col]
        .astype(str)
        .str.replace(",", "", regex=False)  # quitar separador de miles
    )
    df_articulos[precio_promo_col] = pd.to_numeric(df_articulos[precio_promo_col], errors="coerce")

    df_articulos["Valor Comercial"] = df_articulos[stock_col] * df_articulos[precio_promo_col]

    # --- Nombre de salida con fecha actual ---
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    nombre_salida_xlsx = f"Stock-{fecha_hoy}.xlsx"

    with pd.ExcelWriter(nombre_salida_xlsx, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Productos", index=False)
        df_filtrados.to_excel(writer, sheet_name="Filtrados", index=False)
        df_articulos.to_excel(writer, sheet_name="Artículos", index=False)

    print(f"Archivo procesado y guardado en: {nombre_salida_xlsx}")

if __name__ == "__main__":
    procesar_csv()
