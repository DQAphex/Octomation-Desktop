import os
import fitz  # PyMuPDF
import pandas as pd

def detalle_pdfs_por_palabra(ruta_carpeta: str, palabras_buscadas: list):
    total_pdfs = 0
    # Diccionario para almacenar la lista de archivos por cada palabra
    resultados_por_palabra = {palabra: [] for palabra in palabras_buscadas}
    carpetas_premiadas = []
    palabras_lower = [p.lower() for p in palabras_buscadas]

    # os.walk recorre la carpeta y subcarpetas recursivamente
    for raiz, _, archivos in os.walk(ruta_carpeta):
        for archivo in archivos:
            if archivo.lower().endswith(".pdf"):
                total_pdfs += 1
                ruta_completa = os.path.join(raiz, archivo)
                
                try:
                    # Extraer todo el texto del PDF de una sola vez
                    texto_completo = ""
                    with fitz.open(ruta_completa) as doc:
                        for pagina in doc:
                            t = pagina.get_text()
                            if t:
                                texto_completo += t.lower() + "\n"
                    
                    # Verificar cada palabra individualmente para este PDF
                    for palabra_original, palabra_lower in zip(palabras_buscadas, palabras_lower):
                        if palabra_lower in texto_completo:
                            resultados_por_palabra[palabra_original].append({
                                "nombre": archivo,
                                "ruta": ruta_completa
                            })
                            
                except Exception as e:
                    print(f"No se pudo leer el archivo {archivo}: {e}")
                    continue

    print(f"\n--- Resultados Detallados de la Búsqueda ---")
    print(f"Total de PDFs analizados: {total_pdfs}\n")
    
    for palabra, archivos_encontrados in resultados_por_palabra.items():
        print(f"========================================")
        print(f"Palabra: '{palabra}' (Aparece en {len(archivos_encontrados)} PDF(s))")
        print(f"========================================")
        
        if archivos_encontrados:
            for item in archivos_encontrados:
                print(f" - Archivo: {item['nombre']}")
                print(f"   Ruta:    {item['ruta']}")
            rutas_unicas = sorted(list(set(item['ruta'] for item in archivos_encontrados)))
            
            for ruta in rutas_unicas:
                print(f" - Ruta única: {ruta}")
        else:
            print(" - (No se encontró en ningún PDF)")
        print()

def ver_todos_los_metadatos(ruta_carpeta: str):
    for raiz, _, archivos in os.walk(ruta_carpeta):
        for archivo in archivos:
            if archivo.lower().endswith(".pdf"):
                ruta_completa = os.path.join(raiz, archivo)
                try:
                    with fitz.open(ruta_completa) as doc:
                        print(f"Archivo: {archivo}")
                        # Imprime todo el diccionario de metadatos del PDF
                        for clave, valor in doc.metadata.items():
                            print(f"  {clave}: {valor}")
                        print("-" * 40)
                except Exception as e:
                    print(f"Error en {archivo}: {e}")

def listar_directorio_os(ruta_destino):
    try:
        print(f"\n--- Contenido de: {os.path.abspath(ruta_destino)} ---")
        with os.scandir(ruta_destino) as entradas:
            for entrada in entradas:
                if entrada.is_dir():
                    print(f"📁 [Carpeta]  {entrada.name}")
                elif entrada.is_file():
                    print(f"📄 [Archivo]  {entrada.name}")
    except FileNotFoundError:
        print(f"Error: No se encontró la ruta '{ruta_destino}'.")
        
def exportar_pdfs_por_palabra_a_csv(ruta_carpeta: str, palabras_buscadas: list, nombre_csv: str = "resultados_busqueda.csv"):
    total_pdfs = 0
    palabras_lower = [p.lower() for p in palabras_buscadas]
    
    # Lista para almacenar los registros planos para el DataFrame
    registros = []

    # os.walk recorre la carpeta y subcarpetas recursivamente
    for raiz, _, archivos in os.walk(ruta_carpeta):
        for archivo in archivos:
            if archivo.lower().endswith(".pdf"):
                total_pdfs += 1
                ruta_completa = os.path.join(raiz, archivo)
                
                try:
                    # Extraer todo el texto del PDF de una sola vez
                    texto_completo = ""
                    with fitz.open(ruta_completa) as doc:
                        for pagina in doc:
                            t = pagina.get_text()
                            if t:
                                texto_completo += t.lower() + "\n"
                    
                    # Verificar cada palabra individualmente para este PDF
                    for palabra_original, palabra_lower in zip(palabras_buscadas, palabras_lower):
                        if palabra_lower in texto_completo:
                            registros.append({
                                "palabra_clave": palabra_original,
                                "nombre_archivo": archivo,
                                "ruta": ruta_completa
                            })
                            
                except Exception as e:
                    print(f"No se pudo leer el archivo {archivo}: {e}")
                    continue

    print(f"\n--- Proceso Finalizado ---")
    print(f"Total de PDFs analizados: {total_pdfs}")
    print(f"Coincidencias encontradas: {len(registros)}")

    # Crear el DataFrame de Pandas y exportar a CSV
    df = pd.DataFrame(registros)
    df.to_csv(nombre_csv, index=False, encoding="utf-8-sig")
    print(f"Archivo CSV guardado exitosamente como: {nombre_csv}")

# --- EJEMPLO DE USO ---
lista_palabras = ['Food', 'hidrolab', 'anam', 'Société','biodiversa','patagonia','agq']
path = "C:\\Users\\dquioza\\OneDrive - SMU S.A\\Medio Ambiente - CONTROL DIRECTO\\INFORMES"
exportar_pdfs_por_palabra_a_csv(path,lista_palabras,"pdfs.csv")