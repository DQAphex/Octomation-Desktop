import ssl
import easyocr
from img2table.document import PDF
from img2table.ocr import EasyOCR
import pandas as pd

# --- PARCHE PARA CERTIFICADOS CORPORATIVOS ---
ssl._create_default_https_context = ssl._create_unverified_context
# ---------------------------------------------
def showAllScanTables(file_path):
  total_dataframes = []
  try:
      # 1. Configurar el motor de OCR con EasyOCR en español
      ocr_engine = EasyOCR(lang=["es"])
      
      # 2. Cargar el PDF escaneado con img2table
      doc = PDF(file_path)
      
      # 3. Extraer las tablas utilizando el OCR
      print("Analizando documento escaneado en busca de tablas...")
      extracted_tables = doc.extract_tables(ocr=ocr_engine)
      
      # 4. Recorrer los resultados por página
      for num_pagina, tables in extracted_tables.items():
        for idx_tabla, table in enumerate(tables):
          # table.df ya es un DataFrame de Pandas
          df = table.df
          total_dataframes.append(df)
                  
      if total_dataframes:
        return total_dataframes
  except FileNotFoundError:
      print(f"Error: No se encontró el archivo '{file_path}'. Verifica la ruta.")
      return None
  except Exception as e:
      print(f"Ocurrió un error inesperado al procesar el PDF: {e}")
      return None
  
def searchScanTables(file_path, keyword):
  total_dataframes = []
  try:
    # 1. Configurar el motor de OCR con EasyOCR en español
    ocr_engine = EasyOCR(lang=["es"])
    
    # 2. Cargar el PDF escaneado con img2table
    doc = PDF(file_path)
    
    # 3. Extraer las tablas utilizando el OCR
    print("Analizando documento escaneado en busca de tablas...")
    extracted_tables = doc.extract_tables(ocr=ocr_engine)
    
    # 4. Recorrer los resultados por página
    for num_pagina, tables in extracted_tables.items():
      for idx_tabla, table in enumerate(tables):
        # table.df ya es un DataFrame de Pandas
        df = table.df
        encontrada = False
        
        # Buscar la keyword celda por celda en el DataFrame
        for col in df.columns:
          # Convertir toda la columna a texto y buscar
          matches = df[col].astype(str).str.contains(keyword, case=False, na=False)
          if matches.any():
            encontrada = True
            break
        
        # Si la palabra clave está en la tabla, la guardamos
        if encontrada:
          print(f"¡Encontrada en la Página {num_pagina + 1}, Tabla #{idx_tabla + 1}!")
          total_dataframes.append(df)
                
    if total_dataframes:
      return total_dataframes
    else:
      print(f"La palabra '{keyword}' no se encontró en ninguna tabla escaneada.")
      return None
          
  except FileNotFoundError:
    print(f"Error: No se encontró el archivo '{file_path}'. Verifica la ruta.")
    return None
  except Exception as e:
    print(f"Ocurrió un error inesperado al procesar el PDF: {e}")
    return None

# --- EJEMPLO DE USO ---
tablas_encontradas = searchScanTables("ScanBiodiversa.pdf", "DS 609")
print(tablas_encontradas)