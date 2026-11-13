import os
import sys
from pathlib import Path
from plyer import notification 
from paths import DB_DIR
# Obtener la carpeta donde vive este worker.py (outlookChecker)
CURRENT_DIR = Path(__file__).resolve().parent

# Forzar a Python a buscar PRIMERO en la carpeta local de este worker
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

# Limpiar del caché cualquier 'config' previo cargado por otros scripts
if "config" in sys.modules:
  del sys.modules["config"]

# Importar el config.py propio de esta carpeta
from .outlook_config import DOWNLOADS_DIR
from .modules.outlook_agent import procesar_correos



def notificar_windows(titulo: str, mensaje: str) -> None:
  """Muestra una notificación nativa en el escritorio de Windows."""
  try:
    notification.notify(
        title=titulo,
        message=mensaje,
        app_name="Outlook PDF Checker",
        timeout=5,  
    )
  except Exception as e:
    print(f"Error al enviar notificación: {e}")

def run():
  notificar_windows(
        "Lector Cetificados de recepción Activo",
        "El programa está buscando correos con adjuntos PDF.",
    )
  procesar_correos()


if __name__ == "__main__":
  run()