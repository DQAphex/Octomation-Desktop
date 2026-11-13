import sys
from pathlib import Path

# Obtener el directorio actual donde vive ESTE main.py

CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

if "config" in sys.modules:
  del sys.modules["config"]

# from config import FILE_TEMPLATE_DIR

# Agregar el directorio actual al sys.path para que reconozca los módulos internos ("modules", "readers", etc.)
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

# Importación relativa al subproyecto gracias a la inyección en sys.path
from .modules.utils import diegoonthemoon

def run():
  print("Ejecutando proceso en segundo plano...")