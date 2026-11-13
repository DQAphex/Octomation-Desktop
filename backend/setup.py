import subprocess
import sys
from paths import EXECUTION_DIR, DB_DIR

def inicializar_entorno():
    # 1. Crear directorio de datos persistentes si no existe
    DB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Rutas del entorno virtual relativas a la ejecución
    venv_python = EXECUTION_DIR / "venv" / "Scripts" / "python.exe"
    requirements = EXECUTION_DIR / "requirements.txt"

    if requirements.exists():
        subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(requirements)])

def generar_init_bat():
    init_bat_path = EXECUTION_DIR / "init.bat"
    
    # Usar %~dp0 garantiza portabilidad en Windows Batch
    contenido_bat = (
        "@echo off\n"
        'cd /d "%~dp0"\n'
        'start /b "" "%~dp0venv\\Scripts\\pythonw.exe" "%~dp0run_server.pyw"\n'
        "exit\n"
    )
    
    with open(init_bat_path, "w", encoding="utf-8") as f:
        f.write(contenido_bat)

if __name__ == "__main__":
    inicializar_entorno()
    generar_init_bat()