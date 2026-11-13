import os

def exportar_codigo_proyecto(directorio_origen=".", archivo_salida="codigo_consolidado.txt"):
  # Carpetas y extensiones no deseadas que conviene ignorar
  carpetas_ignoradas = {'.git', '__pycache__', '.venv', 'venv', '.vscode', '.idea', 'node_modules','mi_proyecto.egg-info'}
  extensiones_ignoradas = {'.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.exe', '.zip', '.pdf', '.db', '.sqlite', ".csv",".html",".css",".svg",".md"}

  with open(archivo_salida, 'w', encoding='utf-8') as salida:
    for raiz, carpetas, archivos in os.walk(directorio_origen):
      # Excluir carpetas no deseadas del recorrido
      carpetas[:] = [d for d in carpetas if d not in carpetas_ignoradas]

      for nombre_archivo in sorted(archivos):
        # Evitar leer el mismo archivo de salida generado
        if nombre_archivo == os.path.basename(archivo_salida) or nombre_archivo == "mapa_archivos.txt":
          continue

        _, ext = os.path.splitext(nombre_archivo)
        if ext.lower() in extensiones_ignoradas:
          continue

        ruta_completa = os.path.join(raiz, nombre_archivo)
        ruta_relativa = os.path.relpath(ruta_completa, directorio_origen)

        try:
          with open(ruta_completa, 'r', encoding='utf-8') as f:
            contenido_codigo = f.read()

          # 1. TÍTULO
          salida.write(f"=== TÍTULO: {ruta_relativa} ===\n\n")

          # 2. CÓDIGO
          salida.write(contenido_codigo)
          salida.write("\n\n" + "=" * 60 + "\n\n")

        except (UnicodeDecodeError, PermissionError):
          # Omite archivos binarios o sin permisos de lectura
          continue

  print(f"Proceso finalizado. Archivo generado: {archivo_salida}")

if __name__ == "__main__":
  # Ejecuta la función en el directorio actual
  exportar_codigo_proyecto()