import os

def respaldar_archivos_especificos(ruta_carpeta: str, archivo_salida: str = "resumen_codigo.txt"):
    extensiones_validas = (".py", ".json")
    total_procesados = 0

    # Abrimos el archivo de texto en modo escritura (utf-8 para evitar problemas con tildes o caracteres especiales)
    with open(archivo_salida, "w", encoding="utf-8") as salida:
        
        # os.walk recorre la carpeta y todas sus subcarpetas
        for raiz, _, archivos in os.walk(ruta_carpeta):
            for archivo in archivos:
                # Verificamos si el archivo termina en .py o .json (ignorando mayúsculas/minúsculas)
                if archivo.lower().endswith(extensiones_validas):
                    total_procesados += 1
                    ruta_completa = os.path.join(raiz, archivo)
                    
                    # Escribimos los metadatos (nombre y ruta)
                    salida.write("=" * 80 + "\n")
                    salida.write(f"NOMBRE ARCHIVO: {archivo}\n")
                    salida.write(f"RUTA ABSOLUTA : {os.path.abspath(ruta_completa)}\n")
                    salida.write("=" * 80 + "\n")
                    
                    # Intentamos leer y escribir el contenido del archivo de código/configuración
                    try:
                        with open(ruta_completa, "r", encoding="utf-8") as f:
                            contenido = f.read()
                            salida.write(contenido)
                    except Exception as e:
                        salida.write(f"[ERROR AL LEER EL ARCHIVO]: {e}\n")
                    
                    # Dejamos un espacio de separación entre archivo y archivo
                    salida.write("\n\n")

    print(f"\n--- Proceso Finalizado ---")
    print(f"Se recopilaron {total_procesados} archivos (.py y .json).")
    print(f"Guardado exitosamente en: {os.path.abspath(archivo_salida)}")

# --- EJEMPLO DE USO ---
# Reemplaza esta ruta por la carpeta donde tienes tus proyectos
path_proyecto = r"C:\Users\dquioza\OneDrive - SMU S.A\Escritorio\hola\routes\medioambiente\riles\automatizaciones\lectorPdf"
respaldar_archivos_especificos(path_proyecto, "archivos_python_json.txt")