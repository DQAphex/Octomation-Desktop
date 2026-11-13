import os
import sys
from pathlib import Path
from plyer import notification 
from paths import DB_DIR
from .outlook_config import METADATA_DIR
import json


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
from .modules.outlook_agent import descargar_adjuntos
from sqlalchemy import create_engine, text

def get_bp_id(): 
  with open(METADATA_DIR, "r", encoding="utf-8") as metadata:
    datos = json.load(metadata)
  id = datos["id"]
  return id

def getFunctionalData():
  engine = create_engine(
    f"sqlite:///{(DB_DIR / 'processes_registry.db').as_posix()}"
  )

  def getValues(engine, option):
    with engine.connect() as connection:
      result = connection.execute(
        text("""
          SELECT value
          FROM bp_option_values
          WHERE option_id = :option_id
        """),
        {"option_id": option}
      )
      return [row[0] for row in result]
    
    bp_id = get_bp_id()
    q_co = f"{bp_id}.dias_atras_revision"

    dias_atras_revision = getValues(engine, q_co)

    return dias_atras_revision

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
        "Outlook Agent Activo",
        "El programa está buscando correos con adjuntos PDF.",
    )
  descargar_adjuntos()


if __name__ == "__main__":
  run()