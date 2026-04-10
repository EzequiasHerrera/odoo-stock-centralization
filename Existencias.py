import pandas as pd
import os
import chardet
import csv
from datetime import datetime

# ------ EXISTENCIAS.PY: Genera Excel con hojas Productos, Filtrados, Artículos y Categorías ----- #

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

    # ✅ Convertir Precio y Precio Promocional en Productos
    precio_col_prod = df.columns[8]
    precio_promo_col_prod = df.columns[9]

    df[precio_col_prod] = (
        df[precio_col_prod]
        .astype(str)
        .str.replace(",", "", regex=False)
    )
    df[precio_col_prod] = pd.to_numeric(df[precio_col_prod], errors="coerce")

    df[precio_promo_col_prod] = (
        df[precio_promo_col_prod]
        .astype(str)
        .str.replace(",", "", regex=False)
    )
    df[precio_promo_col_prod] = pd.to_numeric(df[precio_promo_col_prod], errors="coerce")

    # --- Construir hoja Filtrados ---
    columna_sku = df.columns[11]   # SKU
    columna_nombre = df.columns[0] # Nombre

    mask_pipe = df[columna_sku].astype(str).str.contains(r"\|", regex=True)
    mask_comb = df[columna_sku].astype(str).str.startswith("Comb")
    mask_box = df[columna_nombre].astype(str).str.contains("Box", case=False, na=False)

    df_filtrados = df[~(mask_pipe | mask_comb | mask_box)]

    # --- Construir hoja Artículos ---
    nombre_col = df_filtrados.columns[0]       # Nombre
    precio_col = df_filtrados.columns[8]       # Precio
    precio_promo_col = df_filtrados.columns[9] # Precio Promocional
    stock_col = df_filtrados.columns[10]       # Stock

    df_articulos = (
        df_filtrados
        .groupby([nombre_col], as_index=False)
        .agg({
            stock_col: "sum",
            precio_col: "first",
            precio_promo_col: "first"
        })
    )

    # ✅ Insertar Categorías en columna B
    df_articulos.insert(1, "Categorías", df_articulos[nombre_col].astype(str).str.split().str[0].str.upper())

    # ✅ Normalizar categorías específicas
    df_articulos["Categorías"] = df_articulos["Categorías"].replace(
        {"VEDETINA": "VEDETTINA", "VEDETINALESS": "VEDETTINA", "VEDETTINALESS": "VEDETTINA"}
    )

    # ✅ Eliminar registros con categorías no deseadas
    # Lista editable de categorías a excluir
    categorias_excluir = ["KIT", "GIFTCARD", "ELEGÍ", "MEJORA", "TESTE"]
    df_articulos = df_articulos[~df_articulos["Categorías"].isin(categorias_excluir)]

    # ✅ Convertir precios y eliminar registros con precio 0
    df_articulos[precio_col] = pd.to_numeric(df_articulos[precio_col], errors="coerce")
    df_articulos[precio_promo_col] = pd.to_numeric(df_articulos[precio_promo_col], errors="coerce")
    df_articulos = df_articulos[df_articulos[precio_col] != 0]

    # ✅ Nueva columna: Valor Comercial
    df_articulos[stock_col] = pd.to_numeric(df_articulos[stock_col], errors="coerce")
    df_articulos["Valor Comercial"] = df_articulos[stock_col] * df_articulos[precio_promo_col]

    # --- Construir hoja Categorías ---
    df_categorias = (
        df_articulos.groupby("Categorías", as_index=False)[stock_col].sum()
        .rename(columns={"Categorías": "Categoría", stock_col: "Stock"})
        .sort_values("Categoría")
    )

    # --- Nombre de salida con fecha actual ---
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    nombre_salida_xlsx = f"Stock-{fecha_hoy}.xlsx"

    with pd.ExcelWriter(nombre_salida_xlsx, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Productos", index=False)
        df_filtrados.to_excel(writer, sheet_name="Filtrados", index=False)
        df_articulos.to_excel(writer, sheet_name="Artículos", index=False)
        df_categorias.to_excel(writer, sheet_name="Categorías", index=False)

        # --- Aplicar formatos ---
        workbook = writer.book
        formato_moneda = workbook.add_format({'num_format': '"$" #,##0,00'})
        formato_general = workbook.add_format({'num_format': '0'})

        for sheet_name, dataframe in {
            "Productos": df,
            "Filtrados": df_filtrados,
            "Artículos": df_articulos,
            "Categorías": df_categorias
        }.items():
            worksheet = writer.sheets[sheet_name]

            # Ajustar ancho de columnas automáticamente
            for i, col in enumerate(dataframe.columns):
                max_len = max(
                    dataframe[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                worksheet.set_column(i, i, max_len)

            if sheet_name == "Productos":
                worksheet.set_column(8, 9, None, formato_moneda)

            if sheet_name == "Filtrados":
                worksheet.set_column(8, 9, None, formato_moneda)

            if sheet_name == "Artículos":
                worksheet.set_column(2, 2, 10, formato_general)   # Stock con ancho fijo 10
                worksheet.set_column(3, 5, 20, formato_moneda)    # Precio, Precio Promocional y Valor Comercial con ancho fijo 20

            if sheet_name == "Categorías":
                worksheet.set_column(0, 0, 20)  # Categoría
                worksheet.set_column(1, 1, 10, formato_general)  # Stock

        # --- Inserciones personalizadas en hoja Categorías ---
        ws_cat = writer.sheets["Categorías"]

        # Ajustar ancho de columna E a 25
        ws_cat.set_column(4, 4, 25)
        
        # 1) TRAJES DE BAÑO: suma de stocks de BIKINI, BODYSUIT y ENTERA
        stock_trajes = df_articulos[
            df_articulos["Categorías"].isin(["BIKINI", "BODYSUIT", "ENTERA"])
        ][stock_col].sum()
        ws_cat.write("E2", "TRAJES DE BAÑO")
        ws_cat.write("F2", stock_trajes)

        # 2) CONJUNTO BIANCA: stock desde hoja Artículos
        stock_bianca = df_articulos.loc[
            df_articulos[nombre_col].str.contains("Conjunto Bianca", case=False, na=False),
            stock_col
        ].sum()
        ws_cat.write("E6", "CONJUNTO BIANCA")
        ws_cat.write("F6", stock_bianca)

        # 3) BRALETTE PSONIAC
        stock_psoniac = df_articulos.loc[
            df_articulos[nombre_col].str.contains("Bralette Psoniac", case=False, na=False),
            stock_col
        ].sum()
        ws_cat.write("E7", "BRALETTE PSONIAC")
        ws_cat.write("F7", stock_psoniac)

        # 4) ARNÉS SOFÍA 2 PIEZAS
        stock_arnes = df_articulos.loc[
            df_articulos[nombre_col].str.contains("Arnes Sofia 2 piezas", case=False, na=False),
            stock_col
        ].sum()
        ws_cat.write("E8", "ARNÉS SOFÍA 2 PIEZAS")
        ws_cat.write("F8", stock_arnes)

        # 5) ENTERA MOSCÚ: sumatoria de todos los artículos que comiencen con "Entera Moscú"
        stock_moscu = df_articulos.loc[
            df_articulos[nombre_col].str.startswith("Entera Moscú", na=False),
            stock_col
        ].sum()
        ws_cat.write("E9", "ENTERA MOSCÚ")
        ws_cat.write("F9", stock_moscu)

        # --- Sumatoria al final de columna B ---
        ultima_fila = len(df_categorias) + 1
        formato_bold = workbook.add_format({'bold': True, 'num_format': '0'})
        ws_cat.write(ultima_fila, 0, "TOTAL", formato_bold)
        ws_cat.write_formula(ultima_fila, 1, f"=SUM(B2:B{ultima_fila})", formato_bold)
    
    print(f"Archivo procesado y guardado en: {nombre_salida_xlsx}")

if __name__ == "__main__":
    procesar_csv()
