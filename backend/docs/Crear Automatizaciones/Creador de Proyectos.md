# Estructura Estándar: Automatizaciones y Procesos

Este documento establece la estructura estándar y mínima requerida para implementar **Automatizaciones** (síncronas/bajo demanda) y **Procesos en Segundo Plano** (*background processes/workers*) en la plataforma.

Las automatizaciones actúan como **subproyectos independientes** que autogestionan la resolución de sus módulos internos (`readers`, `modules`, `utils`) mediante la inyección de su propio directorio en `sys.path`.

---

## 1. Automatización (Ejemplo: Formulario Simple)

### 📁 Estructura Gráfica de Archivos

```plaintext
hola/
  ├── automations/
  │     └── demo/
  │           └── hola_mundo/               <-- Subproyecto
  │                 ├── config.py           <-- Autoubicación de rutas internas
  │                 ├── main.py             <-- Punto de entrada (run)
  │                 └── modules/
  │                       └── saludador.py  <-- Módulo interno
  ├── routes/
  │     └── demo/
  │           └── hola_mundo_route.py       <-- Endpoint HTTP
  └── templates/
        └── demo/
              └── hola_mundo.html           <-- Interfaz HTML

```

---

### 💻 Ejemplo de Código

#### 1. Configuración (`automations/demo/hola_mundo/config.py`)

```python
from pathlib import Path

# Ruta raíz exclusiva de ESTA automatización
BASE_DIR = Path(__file__).resolve().parent

# Rutas internas relativas del subproyecto
MODULES_DIR = BASE_DIR / "modules"


```

#### 2. Módulo Interno (`automations/demo/hola_mundo/modules/saludador.py`)

```python
def generar_saludo(nombre: str) -> str:
  """Lógica interna del módulo."""
  return f"¡Hola, {nombre}! Procesado correctamente."


```

#### 3. Punto de Entrada (`automations/demo/hola_mundo/main.py`)

```python
import sys
from pathlib import Path

# Obtener el directorio actual donde vive ESTE main.py
CURRENT_DIR = Path(__file__).resolve().parent

# Agregar el directorio actual al sys.path para que reconozca los módulos internos ("modules", "readers", etc.)
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

# Importación relativa al subproyecto gracias a la inyección en sys.path
from modules.saludador import generar_saludo

def run(payload: dict = None) -> dict:
  """
  Punto de entrada invocado por los endpoints o backend orquestador.
  """
  payload = payload or {}
  nombre = payload.get("nombre", "Mundo")
  mensaje = generar_saludo(nombre)

  return {
    "status": "success",
    "mensaje": mensaje
  }


```

---

### 🌐 Endpoint HTTP (`routes/demo/hola_mundo_route.py`)

```python
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Importación del punto de entrada usando la ruta mapeada globalmente por pyproject.toml
from automations.demo.hola_mundo.main import run

router = APIRouter(prefix="/demo/hola-mundo", tags=["Demo Hola Mundo"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def ver_formulario(request: Request):
  return templates.TemplateResponse("demo/hola_mundo.html", {"request": request})

@router.post("/run", response_class=HTMLResponse)
async def ejecutar_hola_mundo(request: Request, nombre: str = Form(...)):
  resultado = run({"nombre": nombre})

  return templates.TemplateResponse(
    "demo/hola_mundo.html", 
    {"request": request, "resultado": resultado["mensaje"]}
  )


```

---

### 🎨 Template HTML (`templates/demo/hola_mundo.html`)

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Hola Mundo</title>
</head>
<body>
  <h1>Enviar Nombre</h1>
  <form action="/demo/hola-mundo/run" method="post">
    <label for="nombre">Nombre:</label>
    <input type="text" id="nombre" name="nombre" required>
    <button type="submit">Enviar</button>
  </form>

  {% if resultado %}
    <h2>Resultado:</h2>
    <p>{{ resultado }}</p>
  {% endif %}
</body>
</html>

```

---

## 2. Proceso en Segundo Plano (Ejemplo: Notificación de Windows)

### 📁 Estructura Gráfica de Archivos

```plaintext
hola/
  ├── background_processes/
  │     ├── manager.py                      <-- Gestor global de workers
  │     └── notificador_windows/            <-- Worker en background
  │           ├── metadata.json             <-- Metadatos del proceso
  │           ├── worker.py                 <-- Bucle principal
  │           └── modules/
  │                 └── notifier.py         <-- Módulo interno del worker
  └── routes/
        └── background_processes/
              └── notificador_route.py      <-- Endpoint de control

```

---

### 📄 Metadatos (`background_processes/notificador_windows/metadata.json`)

```json
{
  "id": "notificador_windows",
  "name": "Notificador de Escritorio",
  "description": "Muestra una notificación en Windows cada 60 segundos.",
  "category": "sistema",
  "version": "1.0.0",
  "entry_point": "worker.py",
  "default_interval_seconds": 60,
  "enabled": false
}

```

---

### 💻 Ejemplo de Código

#### 1. Módulo Interno (`background_processes/notificador_windows/modules/notifier.py`)

```python
from plyer import notification

def enviar_notificacion_windows():
  """Genera una notificación flotante en Windows."""
  notification.notify(
    title="Notificación del Sistema",
    message="Hola mundo",
    timeout=5
  )


```

#### 2. Worker (`background_processes/notificador_windows/worker.py`)

```python
import sys
import asyncio
from pathlib import Path
from datetime import datetime

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

from modules.notifier import enviar_notificacion_windows

async def run_notificador_windows(interval_seconds: int = 60):
  """
  Bucle asíncrono gestionado por WorkerManager.
  Soporta cancelación limpia.
  """
  print(f"[{datetime.now()}] Worker 'notificador_windows' INICIADO.")
  try:
    while True:
      enviar_notificacion_windows()
      await asyncio.sleep(interval_seconds)
  except asyncio.CancelledError:
    print(f"[{datetime.now()}] Worker 'notificador_windows' DETENIDO.")
    raise


```

---

### 🌐 Endpoint HTTP de Control (`routes/background_processes/notificador_route.py`)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from background_processes.manager import worker_manager

router = APIRouter(prefix="/api/v1/background/notificador", tags=["Worker Notificador"])

class ToggleProcessDTO(BaseModel):
  enable: bool
  user_id: Optional[int] = None

@router.post("/toggle")
async def toggle_notificador(data: ToggleProcessDTO):
  """
  Endpoint para activar o desactivar el worker en segundo plano.
  """
  try:
    if data.enable:
      success = await worker_manager.start_worker("notificador_windows", user_id=data.user_id)
      mensaje = "Proceso iniciado correctamente." if success else "El proceso ya estaba activo."
    else:
      success = await worker_manager.stop_worker("notificador_windows", user_id=data.user_id)
      mensaje = "Proceso detenido correctamente." if success else "El proceso no estaba activo."

    return {"status": "ok", "message": mensaje}
  except Exception as e:
    raise HTTPException(status_code=400, detail=str(e))


```
