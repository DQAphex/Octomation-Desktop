import pdfplumber
import json

labKeywordJsonPath = "labKeywords.json"

def getTables(file):
    with pdfplumber.open(file) as pdf:
        totalTablas = []
        for page in pdf.pages:
            tablas = page.extract_tables()
            print(page,tablas)

def getLabTableKeyWord(lab):
    with open(labKeywordJsonPath,"r",encoding="utf-8") as keywordsJson:
        keyWordsData = json.load(keywordsJson)
        return keyWordsData[lab]["tabla"]

def buscar_tabla_por_palabra(nombre_archivo: str, palabra_clave: str):
    try:
        with pdfplumber.open(nombre_archivo) as pdf:
            for num_pagina, page in enumerate(pdf.pages):
                tablas = page.extract_tables()
                
                for idx_tabla, tabla in enumerate(tablas):
                    for fila in tabla:
                        for celda in fila:
                            if celda and palabra_clave.lower() in celda.lower():
                                print(f"¡Encontrada en la Página {num_pagina + 1}, Tabla #{idx_tabla + 1}!")
                                return tabla
                                
        print(f"La palabra '{palabra_clave}' no se encontró en ninguna tabla.")
        return None

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{nombre_archivo}'. Verifica la ruta.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al procesar el PDF: {e}")
        return None

def searchMTBKLab(file,keyword):
    totalTables = []
    try:
        with pdfplumber.open(file) as pdf:
            for num_pagina, page in enumerate(pdf.pages):
                tablas = page.extract_tables()
                
                for idx_tabla, tabla in enumerate(tablas):
                    for fila in tabla:
                        for celda in fila:
                            if celda and keyword.lower() in celda.lower():
                                print(f"¡Encontrada en la Página {num_pagina + 1}, Tabla #{idx_tabla + 1}!")
                                totalTables.append(tabla)
            return totalTables  
                                
        print(f"La palabra '{keyword}' no se encontró en ninguna tabla.")
        return None
    
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{keyword}'. Verifica la ruta.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al procesar el PDF: {e}")
        return None

def searchMultipleTableByKeyword(file,lab=None,kw=None):
    print("searchMultipleTableByKeyword")
    if lab != None:
        resultTables = searchMTBKLab(file,getLabTableKeyWord(lab))
        return resultTables
    if kw != None:
        resultTables = searchMTBKLab(file,kw)
        return resultTables

def mergeTables(tableArray):
    # Unir Tablas si el pdf trae la misma tabla pero dividida en varias paginas
    mergedTable = []
    for table in tableArray:
        mergedTable+=table
    return mergedTable

def get_pdf_table(file,lab):
    sgsKeyword = getLabTableKeyWord(lab)
    tabla = buscar_tabla_por_palabra(file,sgsKeyword)
    return tabla

def print_pdf_results(results):
    for parametro,valor in results.items():
        print(f"{parametro}: {valor}")
