# automations/medioambiente/riles/lectorPdf/config.py
from pathlib import Path

# Ruta raíz exclusiva de ESTA automatización
BASE_DIR = Path(__file__).resolve().parent

# Rutas internas relativas
DATA_DIR = BASE_DIR / "Data"
TEMPLATES_DIR = BASE_DIR / "templates"
UTILS_DIR = BASE_DIR / "utils" 

FILE_TEMPLATE_DIR = TEMPLATES_DIR / "mail.html" 