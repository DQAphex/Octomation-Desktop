import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .bp_crawler import (
  SessionLocal,
  BackgroundProcessModel,
  ProcessScheduleModel,
  get_background_proceses,
)

# Instancia global del scheduler con zona horaria definida
scheduler = AsyncIOScheduler(timezone="America/Santiago")


def make_sync_execution_wrapper(func):
  """Envuelve funciones normales (def) para que corran en un thread secundario sin bloquear asyncio."""

  async def wrapper():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, func)

  return wrapper


def register_single_job(process, sched) -> bool:
  """Registra o actualiza un job individual en el scheduler."""
  diccionario_funciones = get_background_proceses()

  if process.clave_modulo not in diccionario_funciones:
    return False

  raw_func = diccionario_funciones[process.clave_modulo].get("run")
  if not raw_func:
    return False

  func_to_run = (
      raw_func
      if asyncio.iscoroutinefunction(raw_func)
      else make_sync_execution_wrapper(raw_func)
  )
  job_id = f"job_{process.id}_{sched.id}"

  scheduler.add_job(
      func_to_run,
      "cron",
      hour=sched.hour,
      minute=sched.minute,
      id=job_id,
      misfire_grace_time=60,
      replace_existing=True,
  )
  print(
      f"Job actualizado/agregado: '{job_id}'"
      f" ({sched.hour:02d}:{sched.minute:02d})"
  )
  return True


def remove_single_job(process_id: int, schedule_id: int):
  """Remueve un job específico del scheduler si existe."""
  job_id = f"job_{process_id}_{schedule_id}"
  if scheduler.get_job(job_id):
    scheduler.remove_job(job_id)
    print(f"Job removido del scheduler: '{job_id}'")


def load_schedules_from_db():
  """Carga inicial de todos los horarios habilitados al arrancar la app."""
  db = SessionLocal()
  try:
    processes = (
        db.query(BackgroundProcessModel)
        .filter(BackgroundProcessModel.enabled == True)
        .all()
    )

    for process in processes:
      schedules = (
          db.query(ProcessScheduleModel)
          .filter(ProcessScheduleModel.process_id == process.id)
          .all()
      )

      for sched in schedules:
        register_single_job(process, sched)
  except Exception as e:
    print(f"Error cargando horarios iniciales: {e}")
  finally:
    db.close()