from pathlib import Path

# Ruta raíz exclusiva de ESTA automatización
BASE_DIR = Path(__file__).resolve().parent

# Rutas internas relativas del subproyecto
SERVICES_DIR = BASE_DIR / "services"
PAGES_DIR = BASE_DIR / "pages"
STATIC_DIR = BASE_DIR / "static"
BP_DIR = BASE_DIR / "backgroundProcesses"
AUTOMATIZACIONES_DIR = BASE_DIR / "automatizaciones"
DB_DIR = BASE_DIR / "data"
FILES_DIR = BASE_DIR / "files"