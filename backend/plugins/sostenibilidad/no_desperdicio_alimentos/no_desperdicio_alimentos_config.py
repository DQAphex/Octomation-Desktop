# ==============================================================================
# 1. Plantilla Corregida: plugin_config.py.template
# ==============================================================================
from pathlib import Path

# Metadata del plugin
PLUGIN_NAME = "no_desperdicio_alimentos"
PLUGIN_VERSION = "0.0.1"

# Ruta raíz absoluta del plugin en tiempo de ejecución
BASE_DIR = Path(__file__).resolve().parent

# Estructura interna de directorios
DATA_DIR = BASE_DIR / "data"
PAGES_DIR = BASE_DIR / "pages"
SERVICES_DIR = BASE_DIR / "services"
STATIC_DIR = BASE_DIR / "static"
BACKGROUND_PROCESSES_DIR = BASE_DIR / "backgroundProcesses"