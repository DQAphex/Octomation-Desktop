import sys
import os
from pathlib import Path

# Importar rutas desde tu módulo paths.py
from paths import EXECUTION_DIR

# Asegurar que el directorio raíz esté en el PATH de Python
os.chdir(EXECUTION_DIR)
if str(EXECUTION_DIR) not in sys.path:
    sys.path.insert(0, str(EXECUTION_DIR))

# Redirigir errores a un archivo log silencioso por si algo falla
log_file = EXECUTION_DIR / "server_error.log"
sys.stdout = open(log_file, "a", encoding="utf-8")
sys.stderr = open(log_file, "a", encoding="utf-8")

try:
    import uvicorn
    from main import app

    if __name__ == "__main__":
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
except Exception as e:
    import traceback
    traceback.print_exc()