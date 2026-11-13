from pathlib import Path

# Ruta raíz exclusiva de ESTA automatización
BASE_DIR = Path(__file__).resolve().parent

# Rutas internas relativas
DATA_DIR = BASE_DIR / "Data"
TEST_PDF_DIR = BASE_DIR / "test pdf"
OCR_DIR = BASE_DIR / "ocr"
READERS_DIR = BASE_DIR / "readers"
RESULTS_DIR = BASE_DIR / "results"
TESTS_DIR = BASE_DIR / "results"
UTILS_DIR = BASE_DIR / "utils"

# Archivos clave de configuración y datos
DATA_KEYWORDS_FILE = BASE_DIR / "dataKeywords.json"
LAB_KEYWORDS_FILE = BASE_DIR / "labKeywords.json"
LOCALES_CSV = DATA_DIR / "Locales.csv"