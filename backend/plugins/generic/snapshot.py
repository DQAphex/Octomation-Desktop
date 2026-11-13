import os
from paths import ROOT_DIR

def mapear_directorio(ruta_raiz, archivo_salida=None):
  """Recorre la ruta raíz y subcarpetas, mostrando y guardando los archivos,

  excluyendo la carpeta venv.
  """
  # Convertir a string por seguridad si viene como Path de pathlib
  ruta_raiz_str = str(ruta_raiz)
  print(f"\n[+] Mapeando la ruta: {ruta_raiz_str}\n")

  resultado = []

  for directorio_actual, subdirectorios, archivos in os.walk(ruta_raiz_str):
    # Excluir la carpeta 'venv' modificando la lista de subdirectorios in-place
    if "venv" in subdirectorios:
      subdirectorios.remove("venv")

    # Calcular la profundidad para dar formato de árbol visual
    nivel = directorio_actual.replace(ruta_raiz_str, "").count(os.sep)
    indentacion = "  " * nivel
    carpeta_actual = os.path.basename(directorio_actual) or directorio_actual

    # Agregar carpeta a la lista
    linea_carpeta = f"{indentacion}📁 {carpeta_actual}/"
    print(linea_carpeta)
    resultado.append(linea_carpeta)

    # Agregar archivos de la carpeta
    for archivo in archivos:
      indentacion_archivo = "  " * (nivel + 1)
      linea_archivo = f"{indentacion_archivo}📄 {archivo}"
      print(linea_archivo)
      resultado.append(linea_archivo)

  # Guardar en un archivo de texto si se especifica
  if archivo_salida:
    with open(archivo_salida, "w", encoding="utf-8") as f:
      f.write("\n".join(resultado))
    print(
        f"\n[✔] ¡Mapeo completado con éxito! Guardado en: {archivo_salida}"
    )
  return(resultado)


if __name__ == "__main__":
  # CONFIGURACIÓN:
  CARPETA_RAIZ = ROOT_DIR

  # Nombre del archivo de texto donde se guardará el resultado (opcional)
  ARCHIVO_REPORTE = "mapa_archivos.txt"

  mapear_directorio(CARPETA_RAIZ, ARCHIVO_REPORTE)