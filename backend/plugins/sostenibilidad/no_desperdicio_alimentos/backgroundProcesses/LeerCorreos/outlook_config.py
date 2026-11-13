from pathlib import Path

# Ruta raíz exclusiva de ESTA automatización
BASE_DIR = Path(__file__).resolve().parent

# Rutas internas relativas del subproyecto
MODULES_DIR = BASE_DIR / "modules"
DOWNLOADS_DIR = BASE_DIR / "downloads"
METADATA_DIR = BASE_DIR / "metadata.json"