import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
    
from datetime import datetime
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates

from pydantic import BaseModel
from typing import Optional
# Librerías de Scheduler de procesos en segundo plano
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Importar rutas centralizadas desde paths.py
from paths import TEMPLATES_DIR, STATIC_DIR, DB_DIR, PLUGINS_DIR

# Importar módulos de endpoints
# from routes.documentation import router as doc_router
from core.plugin_manager import PluginManager


from pydantic import BaseModel, Field

# from functools import partialf
from pytz import timezone # O usa zoneinfo en Python 3.9+

# Importar funciones y modelos desde tu gestor bp_crawler
from core.bp_crawler import (
    get_background_proceses,
    get_bp_schedule_by_id,
    update_columna_orm,
    add_schedule_to_process,
    delete_schedule_to_process,
    SessionLocal,
    BackgroundProcessModel,
    ProcessScheduleModel,
    BPOptionsModel,
    BPOptionValueModel,
    build_option_id,
    ExecutionStatus,
    update_schedule_to_process
)

from core.scheduler_service import (
    scheduler,
    load_schedules_from_db,
    register_single_job,
    remove_single_job,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
  # 1. Cargar la base de datos al scheduler al iniciar
  load_schedules_from_db()

  # 2. Iniciar el scheduler
  scheduler.start()
  print("Scheduler iniciado correctamente.")

  yield

  # 3. Apagar al cerrar FastAPI
  scheduler.shutdown()
  print("Scheduler detenido.")


# Única instancia de FastAPI para toda la app
app = FastAPI(
  title="Automatizaciones | Sostenibilidad",
  lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
background_processes = get_background_proceses()

plugin_manager = PluginManager(app=app, project_root=BASE_DIR)

app.state.plugin_manager = plugin_manager

plugin_manager.discover_and_load()

templates = plugin_manager.get_jinja_templates()

# Imprimir resumen de inicialización en consola
print("=" * 60)
print(
    f"[PLUGIN ENGINE] Carga finalizada. {len(plugin_manager.loaded_plugins)} routers integrados:"
)
for loaded in plugin_manager.loaded_plugins:
  print(f"  - {loaded}")

if plugin_manager.failed_plugins:
  print(
      f"[PLUGIN ENGINE] {len(plugin_manager.failed_plugins)} plugin(s) no pudieron cargarse:"
  )
  for failure in plugin_manager.failed_plugins:
    print(f"  - {failure['plugin']}: {failure['error']}")
    if failure.get("hint"):
      print(f"    -> {failure['hint']}")
print("=" * 60)

# Endpoint raíz principal
@app.get("/")
async def inicio(request: Request):
  datos = {
    "titulo": "Panel de Automatizaciones | Sostenibilidad"
  }
  return templates.TemplateResponse(
    request=request,
    name="index.html",
    context=datos
  )

# Endpoint global de automatizaciones (lee el arbol OpenAPI de toda la app)
@app.get("/automatizaciones")
def automatizaciones(request: Request):
  openapi = app.openapi()
  arbol = {} 
  for path, methods in openapi["paths"].items():
    for method, info in methods.items():
      tags = info.get("tags", ["Sin categoría"])
      for tag in tags:
        arbol.setdefault(tag, []).append({
          "titulo": info.get("summary") or path,
          "descripcion": info.get("description"),
          "ruta": path,
          "metodo": method.upper()
        })

  return templates.TemplateResponse(
    request, 
    name="automatizaciones.html", 
    context={"titulo": "Automatizaciones", "arbol": arbol}
  )

@app.get("/loaded-routers")
def get_loaded_routers():
  return {
    "lodaded_routers": plugin_manager.get_loaded_routers(),
    "failed_plugins": plugin_manager.failed_plugins,
    "dependencies": plugin_manager.dependency_manager.get_report(),
  }

@app.get("/plugins/status")
def get_plugins_status():
  """Estado de carga de plugins y dependencias resueltas al iniciar."""
  return plugin_manager.get_status()

@app.get("/background-processes")
def background_proceses(request: Request):
  procesos = get_background_proceses()
  return templates.TemplateResponse(
    request,
    name = "background-processes.html",
    context={"titulo":"Procesos en segundo plano", "procesos":procesos}
  )

@app.get("/background-processes-all")
def all_background_proceses():
  procesos = get_background_proceses()
  return procesos

@app.post("/background-process/run/{process_id}")
def run_background_process(process_id: str):
  proceso = None

  for clave, data in background_processes.items():
    if data["metadata"].get("id") == process_id:
      proceso = data
      break

  if not proceso:
    raise HTTPException(
      status_code=404,
      detail=f"Proceso '{process_id}' no encontrado."
    )

  try:
    resultado = proceso["run"]()

    return {
      "message": "Proceso ejecutado correctamente.",
      "process_id": process_id,
      "result": resultado
    }

  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Error ejecutando el proceso: {str(e)}"
    )

@app.get("/background-process-schedule/{process_id}")
def read_bp_schedule_by_id(process_id: str):
  resultado = get_bp_schedule_by_id(process_id)

  if "error" in resultado:
    raise HTTPException(status_code=404, detail=resultado["error"])

  return resultado

@app.post("/background-process-schedule/{process_id}")
def enable_or_disable_schedule_by_id(process_id: str):
  resultado = get_bp_schedule_by_id(process_id)

  if "error" in resultado:
    raise HTTPException(status_code=404, detail=resultado["error"])

  Actualstatus = resultado["enabled"]
  Newstatus = not Actualstatus
  update_columna_orm(process_id,Newstatus)

  return get_bp_schedule_by_id(process_id)

class ScheduleCreate(BaseModel):
  hour: int = Field(..., ge=0, le=23, description="Hora en formato 24h (0-23)")
  minute: int = Field(..., ge=0, le=59, description="Minuto (0-59)")


@app.post("/background-process-schedule/{process_id}/add")
def create_schedule_endpoint(process_id: str, schedule: ScheduleCreate):
  resultado = add_schedule_to_process(
      process_id=process_id, hour=schedule.hour, minute=schedule.minute
  )

  if "error" in resultado:
    raise HTTPException(status_code=400, detail=resultado["error"])

  db = SessionLocal()
  try:
    process = (
        db.query(BackgroundProcessModel)
        .filter(BackgroundProcessModel.id == process_id)
        .first()
    )
    sched = (
        db.query(ProcessScheduleModel)
        .filter(
            ProcessScheduleModel.process_id == process_id,
            ProcessScheduleModel.hour == schedule.hour,
            ProcessScheduleModel.minute == schedule.minute,
        )
        .first()
    )

    if process and sched and process.enabled:
      register_single_job(process, sched)
  finally:
    db.close()

  return resultado

@app.delete("/background-process-schedule/item/{scheduleId}")
def delete_schedule_endpoint(scheduleId: int):
  db = SessionLocal()
  process_id = None
  try:
    sched = (
        db.query(ProcessScheduleModel)
        .filter(ProcessScheduleModel.id == scheduleId)
        .first()
    )
    if sched:
      process_id = sched.process_id
  finally:
    db.close()

  delete_schedule_to_process(scheduleId)

  if process_id:
    remove_single_job(process_id, scheduleId)

  return {"message": "Horario eliminado correctamente"}

@app.put("/background-process-schedule/item/{scheduleId}")
def update_schedule_endpoint(scheduleId: int, schedule: ScheduleCreate):
  resultado = update_schedule_to_process(
      schedule_id=scheduleId, hour=schedule.hour, minute=schedule.minute
  )

  if "error" in resultado:
    raise HTTPException(status_code=400, detail=resultado["error"])

  return resultado

@app.get("/background-process-options")
def get_background_options(id: str):
  db = SessionLocal()

  try:
    result = (
      db.query(BPOptionsModel)
      .filter(
        BPOptionsModel.background_processes_id == id
      )
      .all()
    )

    return [
      {
        "id": option.id,
        "key": option.key,
        "name": option.name,
        "description": option.description,
        "option_type": option.option_type,
        "multiple": option.multiple,
        "values": [
          {
            "id": value.id,
            "value": value.value
          }
          for value in option.values
        ]
      }
      for option in result
    ]

  except Exception as e:
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()


class BPOptionRequest(BaseModel):
  key: str
  name: str
  description: Optional[str] = None
  option_type: str
  multiple: bool = False
  values: list[str] = []


@app.post("/background-process-options")
def create_background_option(
  id: str,
  data: BPOptionRequest
):
  db = SessionLocal()

  try:
    process = (
      db.query(BackgroundProcessModel)
      .filter(BackgroundProcessModel.id == id)
      .first()
    )

    if not process:
      return {
        "error": f"El proceso '{id}' no existe."
      }

    existing = (
      db.query(BPOptionsModel)
      .filter(
        BPOptionsModel.background_processes_id == id,
        BPOptionsModel.key == data.key
      )
      .first()
    )

    if existing:
      return {
        "error": (
          f"La opción '{data.key}' "
          "ya existe para este proceso."
        )
      }

    if not data.multiple and len(data.values) > 1:
      return {
        "error": (
          "Esta opción solo permite un valor."
        )
      }

    option_id = build_option_id(id, data.key)

    option = BPOptionsModel(
      id=option_id,
      background_processes_id=id,
      key=data.key,
      name=data.name,
      description=data.description,
      option_type=data.option_type,
      multiple=data.multiple
    )

    db.add(option)

    for value in data.values:
      option.values.append(
        BPOptionValueModel(value=str(value))
      )

    db.commit()
    db.refresh(option)

    return {
      "message": "Opción creada correctamente.",
      "option": {
        "id": option.id,
        "key": option.key,
        "name": option.name,
        "description": option.description,
        "option_type": option.option_type,
        "multiple": option.multiple,
        "values": [
          {
            "id": value.id,
            "value": value.value
          }
          for value in option.values
        ]
      }
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()


@app.put("/background-process-options/{option_id}")
def update_background_option(
  option_id: str,
  data: BPOptionRequest
):
  db = SessionLocal()

  try:
    option = (
      db.query(BPOptionsModel)
      .filter(BPOptionsModel.id == option_id)
      .first()
    )

    if not option:
      return {
        "error": (
          f"La opción '{option_id}' "
          "no existe."
        )
      }

    if not data.multiple and len(data.values) > 1:
      return {
        "error": (
          "Esta opción solo permite un valor."
        )
      }

    if data.key != option.key:
      new_id = build_option_id(
        option.background_processes_id,
        data.key
      )

      existing = (
        db.query(BPOptionsModel)
        .filter(BPOptionsModel.id == new_id)
        .first()
      )

      if existing:
        return {
          "error": (
            f"La opción '{data.key}' "
            "ya existe."
          )
        }

      option.id = new_id
      option.key = data.key

    option.name = data.name
    option.description = data.description
    option.option_type = data.option_type
    option.multiple = data.multiple

    option.values.clear()

    for value in data.values:
      option.values.append(
        BPOptionValueModel(value=str(value))
      )

    db.commit()
    db.refresh(option)

    return {
      "message": "Opción actualizada correctamente.",
      "option": {
        "id": option.id,
        "key": option.key,
        "name": option.name,
        "description": option.description,
        "option_type": option.option_type,
        "multiple": option.multiple,
        "values": [
          {
            "id": value.id,
            "value": value.value
          }
          for value in option.values
        ]
      }
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()


@app.delete("/background-process-options/{option_id}")
def delete_background_option(option_id: str):
  db = SessionLocal()

  try:
    option = (
      db.query(BPOptionsModel)
      .filter(BPOptionsModel.id == option_id)
      .first()
    )

    if not option:
      return {
        "error": (
          f"La opción '{option_id}' "
          "no existe."
        )
      }

    db.delete(option)
    db.commit()

    return {
      "message": "Opción eliminada correctamente.",
      "id": option_id
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()

class BPOptionValueRequest(BaseModel):
  value: str


@app.post("/background-process-option-values")
def create_background_option_value(
  option_id: str,
  data: BPOptionValueRequest
):
  db = SessionLocal()

  try:
    option = (
      db.query(BPOptionsModel)
      .filter(BPOptionsModel.id == option_id)
      .first()
    )

    if not option:
      return {
        "error": f"La opción '{option_id}' no existe."
      }

    if not option.multiple and len(option.values) >= 1:
      return {
        "error": (
          "Esta opción no permite agregar "
          "más de un valor."
        )
      }

    if len(data.value) > 500:
      return {
        "error": (
          "El valor no puede superar "
          "los 500 caracteres."
        )
      }

    new_value = BPOptionValueModel(
      option_id=option_id,
      value=data.value
    )

    db.add(new_value)
    db.commit()
    db.refresh(new_value)

    return {
      "message": "Valor agregado correctamente.",
      "value": {
        "id": new_value.id,
        "option_id": new_value.option_id,
        "value": new_value.value
      }
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()


@app.put("/background-process-option-values/{value_id}")
def update_background_option_value(
  value_id: int,
  data: BPOptionValueRequest
):
  db = SessionLocal()

  try:
    option_value = (
      db.query(BPOptionValueModel)
      .filter(BPOptionValueModel.id == value_id)
      .first()
    )

    if not option_value:
      return {
        "error": (
          f"El valor con ID {value_id} "
          "no existe."
        )
      }

    if len(data.value) > 500:
      return {
        "error": (
          "El valor no puede superar "
          "los 500 caracteres."
        )
      }

    option_value.value = data.value

    db.commit()
    db.refresh(option_value)

    return {
      "message": "Valor actualizado correctamente.",
      "value": {
        "id": option_value.id,
        "option_id": option_value.option_id,
        "value": option_value.value
      }
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()


@app.delete("/background-process-option-values/{value_id}")
def delete_background_option_value(value_id: int):
  db = SessionLocal()

  try:
    option_value = (
      db.query(BPOptionValueModel)
      .filter(BPOptionValueModel.id == value_id)
      .first()
    )

    if not option_value:
      return {
        "error": (
          f"El valor con ID {value_id} "
          "no existe."
        )
      }

    db.delete(option_value)
    db.commit()

    return {
      "message": "Valor eliminado correctamente.",
      "id": value_id
    }

  except Exception as e:
    db.rollback()
    return {
      "error": f"Ocurrió el error: {str(e)}"
    }

  finally:
    db.close()

@app.get("/health")
def health():
  
  return "Servidor Activo"


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )