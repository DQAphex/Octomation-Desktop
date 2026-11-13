import enum
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
  Column, Integer, String, Boolean, DateTime,
  ForeignKey, Enum, CheckConstraint,
  UniqueConstraint, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from paths import PLUGINS_DIR, DB_DIR


# ------------------------------------------------------------------
# 1. Base de datos
# ------------------------------------------------------------------

PROCESSES_DB_PATH = DB_DIR / "processes_registry.db"
DATABASE_URL = f"sqlite:///{PROCESSES_DB_PATH.as_posix()}"

engine = create_engine(
  DATABASE_URL,
  connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
  autocommit=False,
  autoflush=False,
  bind=engine
)

Base = declarative_base()


class ExecutionStatus(str, enum.Enum):
  PENDING = "PENDING"
  RUNNING = "RUNNING"
  SUCCESS = "SUCCESS"
  FAILED = "FAILED"


class BackgroundProcessModel(Base):
  __tablename__ = "background_processes"

  id = Column(String(100), primary_key=True)
  clave_modulo = Column(String(255), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(500), nullable=True)
  category = Column(String(100), nullable=True)
  version = Column(String(50), nullable=True)
  enabled = Column(Boolean, default=False, nullable=False)
  last_run = Column(DateTime, nullable=True)
  updated_at = Column(
    DateTime,
    default=datetime.now,
    onupdate=datetime.now
  )

  schedules = relationship(
    "ProcessScheduleModel",
    back_populates="process",
    cascade="all, delete-orphan"
  )

  options = relationship(
    "BPOptionsModel",
    back_populates="process",
    cascade="all, delete-orphan"
  )


class BPOptionsModel(Base):
  __tablename__ = "bp_options"

  id = Column(String(100), primary_key=True)
  background_processes_id = Column(
    String(100),
    ForeignKey(
      "background_processes.id",
      ondelete="CASCADE"
    ),
    nullable=False
  )
  key = Column(String(100), nullable=False)
  name = Column(String(255), nullable=False)
  description = Column(String(500), nullable=True)
  option_type = Column(String(50), nullable=False)
  multiple = Column(Boolean, default=False, nullable=False)

  process = relationship(
    "BackgroundProcessModel",
    back_populates="options"
  )

  values = relationship(
    "BPOptionValueModel",
    back_populates="option",
    cascade="all, delete-orphan"
  )

  __table_args__ = (
    UniqueConstraint(
      "background_processes_id",
      "key",
      name="uq_bp_option_process_key"
    ),
  )


class BPOptionValueModel(Base):
  __tablename__ = "bp_option_values"

  id = Column(Integer, primary_key=True, autoincrement=True)
  option_id = Column(
    String(100),
    ForeignKey(
      "bp_options.id",
      ondelete="CASCADE"
    ),
    nullable=False
  )
  value = Column(String(500), nullable=False)

  option = relationship(
    "BPOptionsModel",
    back_populates="values"
  )


class ProcessScheduleModel(Base):
  __tablename__ = "process_schedules"

  id = Column(Integer, primary_key=True, autoincrement=True)
  process_id = Column(
    String(100),
    ForeignKey(
      "background_processes.id",
      ondelete="CASCADE"
    ),
    nullable=False
  )
  hour = Column(Integer, nullable=False)
  minute = Column(Integer, nullable=False)
  status = Column(
    Enum(ExecutionStatus),
    default=ExecutionStatus.PENDING,
    nullable=False
  )
  last_executed_at = Column(DateTime, nullable=True)
  created_at = Column(DateTime, default=datetime.now)

  __table_args__ = (
    CheckConstraint(
      "hour >= 0 AND hour <= 23",
      name="check_valid_hour"
    ),
    CheckConstraint(
      "minute >= 0 AND minute <= 59",
      name="check_valid_minute"
    ),
    UniqueConstraint(
      "process_id",
      "hour",
      "minute",
      name="uq_process_schedule"
    ),
  )

  process = relationship(
    "BackgroundProcessModel",
    back_populates="schedules"
  )


Base.metadata.create_all(bind=engine)


# ------------------------------------------------------------------
# 2. Configuración
# ------------------------------------------------------------------

bp_dir = PLUGINS_DIR
str_bp_dir = str(bp_dir.resolve())

if str_bp_dir not in sys.path:
  sys.path.insert(0, str_bp_dir)


def build_option_id(process_id: str, option_key: str) -> str:
  return f"{process_id}.{option_key}"


def validate_option_metadata(option: dict) -> bool:
  for field in ("key", "name", "option_type"):
    if field not in option:
      print(f"Advertencia: falta '{field}' en una opción.")
      return False

  if not isinstance(option["key"], str):
    print("Advertencia: 'key' debe ser un string.")
    return False

  if not isinstance(option["name"], str):
    print("Advertencia: 'name' debe ser un string.")
    return False

  if not isinstance(option["option_type"], str):
    print("Advertencia: 'option_type' debe ser un string.")
    return False

  return True


# ------------------------------------------------------------------
# 3. Sincronización de opciones
# ------------------------------------------------------------------

def sync_options_to_db(db, process_id: str, options_config: list):
  for option_config in options_config:
    if not isinstance(option_config, dict):
      print("Advertencia: opción inválida.")
      continue

    if not validate_option_metadata(option_config):
      continue

    option_key = option_config["key"]
    option_id = build_option_id(process_id, option_key)

    option = (
      db.query(BPOptionsModel)
      .filter(BPOptionsModel.id == option_id)
      .first()
    )

    if not option:
      option = BPOptionsModel(
        id=option_id,
        background_processes_id=process_id,
        key=option_key,
        name=option_config["name"],
        description=option_config.get("description", ""),
        option_type=option_config["option_type"],
        multiple=option_config.get("multiple", False)
      )
      db.add(option)
    else:
      option.name = option_config["name"]
      option.description = option_config.get(
        "description",
        option.description
      )
      option.option_type = option_config["option_type"]
      option.multiple = option_config.get(
        "multiple",
        False
      )


# ------------------------------------------------------------------
# 4. Sincronización de procesos
# ------------------------------------------------------------------

def sync_processes_to_db(diccionario_funciones):
  db = SessionLocal()

  try:
    for clave, data in diccionario_funciones.items():
      meta = data["metadata"]
      process_id = meta.get("id", clave)

      db_process = (
        db.query(BackgroundProcessModel)
        .filter(BackgroundProcessModel.id == process_id)
        .first()
      )

      if not db_process:
        db_process = BackgroundProcessModel(
          id=process_id,
          clave_modulo=clave,
          name=meta.get("name", process_id),
          description=meta.get("description", ""),
          category=meta.get("category", "general"),
          version=meta.get("version", "1.0.0"),
          enabled=meta.get("enabled", False)
        )
        db.add(db_process)
      else:
        db_process.clave_modulo = clave
        db_process.name = meta.get("name", db_process.name)
        db_process.description = meta.get(
          "description",
          db_process.description
        )
        db_process.category = meta.get(
          "category",
          db_process.category
        )
        db_process.version = meta.get(
          "version",
          db_process.version
        )

      db.flush()

      meta["id"] = db_process.id
      meta["enabled"] = db_process.enabled

      # ------------------------------------------------------------
      # Horarios
      # ------------------------------------------------------------

      for sched in meta.get("schedules", []):
        if not isinstance(sched, dict):
          continue

        hour = sched.get("hour")
        minute = sched.get("minute")

        if hour is None or minute is None:
          continue

        if not isinstance(hour, int) or not isinstance(minute, int):
          continue

        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
          continue

        existing_schedule = (
          db.query(ProcessScheduleModel)
          .filter(
            ProcessScheduleModel.process_id == process_id,
            ProcessScheduleModel.hour == hour,
            ProcessScheduleModel.minute == minute
          )
          .first()
        )

        if not existing_schedule:
          db.add(
            ProcessScheduleModel(
              process_id=process_id,
              hour=hour,
              minute=minute
            )
          )

      # ------------------------------------------------------------
      # Opciones
      # ------------------------------------------------------------

      sync_options_to_db(
        db,
        process_id,
        meta.get("options", [])
      )

    db.commit()

  except Exception as e:
    db.rollback()
    print(
      f"Error al sincronizar procesos "
      f"en la base de datos: {e}"
    )

  finally:
    db.close()


# ------------------------------------------------------------------
# 5. Descubrimiento de procesos
# ------------------------------------------------------------------

def get_background_proceses():
  diccionario_funciones = {}

  for archivo in bp_dir.rglob("worker.py"):
    if archivo.name.startswith("__"):
      continue

    ruta_relativa = archivo.relative_to(bp_dir)
    archivo_metadata = archivo.parent / "metadata.json"
    metadata = {}

    if archivo_metadata.exists():
      try:
        with open(
          archivo_metadata,
          "r",
          encoding="utf-8"
        ) as f:
          metadata = json.load(f)
      except Exception as e:
        print(
          f"Error leyendo "
          f"{archivo_metadata}: {e}"
        )
        continue
    else:
      print(
        f"Advertencia: {archivo} "
        "no tiene metadata.json."
      )

    clave_modulo = str(
      ruta_relativa.with_suffix("")
    ).replace("\\", "/")

    partes_ruta = [
      bp_dir.name
    ] + list(
      ruta_relativa
      .with_suffix("")
      .parts
    )

    nombre_modulo_completo = ".".join(partes_ruta)

    spec = importlib.util.spec_from_file_location(
      nombre_modulo_completo,
      archivo
    )

    if not spec or not spec.loader:
      print(
        f"Advertencia: no se pudo crear "
        f"spec para {archivo}."
      )
      continue

    modulo = importlib.util.module_from_spec(spec)

    modulo.__package__ = (
      nombre_modulo_completo.rsplit(".", 1)[0]
    )

    sys.modules[nombre_modulo_completo] = modulo

    try:
      spec.loader.exec_module(modulo)

      func_run = getattr(modulo, "run", None)

      if callable(func_run):
        diccionario_funciones[clave_modulo] = {
          "run": func_run,
          "metadata": metadata
        }
      else:
        print(
          f"Advertencia: {archivo} "
          "no tiene una función 'run'."
        )

    except Exception as e:
      print(
        f"Error al cargar "
        f"{archivo}: {e}"
      )
      sys.modules.pop(
        nombre_modulo_completo,
        None
      )

  sync_processes_to_db(diccionario_funciones)

  return diccionario_funciones


# ------------------------------------------------------------------
# 6. Obtener proceso
# ------------------------------------------------------------------

def get_bp_schedule_by_id(process_id: str) -> dict:
  db = SessionLocal()

  try:
    process = (
      db.query(BackgroundProcessModel)
      .filter(
        BackgroundProcessModel.id == process_id
      )
      .first()
    )

    if not process:
      return {
        "error": (
          f"Proceso con ID '{process_id}' "
          "no fue encontrado."
        )
      }

    return {
      "id": process.id,
      "clave_modulo": process.clave_modulo,
      "name": process.name,
      "description": process.description,
      "category": process.category,
      "version": process.version,
      "enabled": process.enabled,
      "last_run": (
        process.last_run.isoformat()
        if process.last_run
        else None
      ),
      "updated_at": (
        process.updated_at.isoformat()
        if process.updated_at
        else None
      ),
      "schedules": [
        {
          "id": sched.id,
          "hour": sched.hour,
          "minute": sched.minute,
          "status": (
            sched.status.value
            if isinstance(
              sched.status,
              ExecutionStatus
            )
            else sched.status
          ),
          "last_executed_at": (
            sched.last_executed_at.isoformat()
            if sched.last_executed_at
            else None
          ),
          "created_at": (
            sched.created_at.isoformat()
            if sched.created_at
            else None
          )
        }
        for sched in process.schedules
      ],
      "options": [
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
        for option in process.options
      ]
    }

  finally:
    db.close()


# ------------------------------------------------------------------
# 7. Actualizar estado
# ------------------------------------------------------------------

def update_columna_orm(
  process_id: str,
  nuevo_estado: bool
):
  db = SessionLocal()

  try:
    process = (
      db.query(BackgroundProcessModel)
      .filter(
        BackgroundProcessModel.id == process_id
      )
      .first()
    )

    if process:
      process.enabled = nuevo_estado
      db.commit()

  except Exception as e:
    db.rollback()
    print(
      f"Error al actualizar estado: {e}"
    )

  finally:
    db.close()


# ------------------------------------------------------------------
# 8. Agregar horario
# ------------------------------------------------------------------

def add_schedule_to_process(
  process_id: str,
  hour: int,
  minute: int
) -> dict:

  if not 0 <= hour <= 23:
    return {
      "error": (
        "La hora debe estar en el rango "
        "de 0 a 23."
      )
    }

  if not 0 <= minute <= 59:
    return {
      "error": (
        "El minuto debe estar en el rango "
        "de 0 a 59."
      )
    }

  db = SessionLocal()

  try:
    process = (
      db.query(BackgroundProcessModel)
      .filter(
        BackgroundProcessModel.id == process_id
      )
      .first()
    )

    if not process:
      return {
        "error": (
          f"Proceso con ID '{process_id}' "
          "no fue encontrado."
        )
      }

    existing_schedule = (
      db.query(ProcessScheduleModel)
      .filter(
        ProcessScheduleModel.process_id == process_id,
        ProcessScheduleModel.hour == hour,
        ProcessScheduleModel.minute == minute
      )
      .first()
    )

    if existing_schedule:
      return {
        "error": (
          f"El horario {hour:02d}:{minute:02d} "
          "ya existe para este proceso."
        )
      }

    new_schedule = ProcessScheduleModel(
      process_id=process_id,
      hour=hour,
      minute=minute
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return {
      "id": new_schedule.id,
      "process_id": new_schedule.process_id,
      "hour": new_schedule.hour,
      "minute": new_schedule.minute,
      "status": new_schedule.status.value,
      "message": "Horario agregado exitosamente."
    }

  except Exception as e:
    db.rollback()
    return {
      "error": (
        f"Error al guardar el horario: {str(e)}"
      )
    }

  finally:
    db.close()


# ------------------------------------------------------------------
# 9. Eliminar horario
# ------------------------------------------------------------------

def delete_schedule_to_process(scheduleId: int):
  print("borrando")
  db = SessionLocal()

  try:
    db.query(
      ProcessScheduleModel
    ).filter(
      ProcessScheduleModel.id == scheduleId
    ).delete(
      synchronize_session=False
    )

    db.commit()

    return "listo"

  except Exception as e:
    db.rollback()
    print(
      f"Error al eliminar horario: {e}"
    )
    raise e

  finally:
    db.close()


# ------------------------------------------------------------------
# 10. Actualizar horario
# ------------------------------------------------------------------

def update_schedule_to_process(
  schedule_id: int,
  hour: int,
  minute: int
) -> dict:

  if not 0 <= hour <= 23:
    return {
      "error": (
        "La hora debe estar en el rango "
        "de 0 a 23."
      )
    }

  if not 0 <= minute <= 59:
    return {
      "error": (
        "El minuto debe estar en el rango "
        "de 0 a 59."
      )
    }

  db = SessionLocal()

  try:
    schedule = (
      db.query(ProcessScheduleModel)
      .filter(
        ProcessScheduleModel.id == schedule_id
      )
      .first()
    )

    if not schedule:
      return {
        "error": (
          f"El horario con ID {schedule_id} "
          "no existe."
        )
      }

    existing = (
      db.query(ProcessScheduleModel)
      .filter(
        ProcessScheduleModel.process_id == schedule.process_id,
        ProcessScheduleModel.hour == hour,
        ProcessScheduleModel.minute == minute,
        ProcessScheduleModel.id != schedule_id
      )
      .first()
    )

    if existing:
      return {
        "error": (
          f"Ya existe un horario a las "
          f"{hour:02d}:{minute:02d}."
        )
      }

    schedule.hour = hour
    schedule.minute = minute

    db.commit()

    return {
      "message": (
        "Horario actualizado correctamente."
      )
    }

  except Exception as e:
    db.rollback()
    return {
      "error": (
        f"Error al actualizar el horario: "
        f"{str(e)}"
      )
    }

  finally:
    db.close()


# ------------------------------------------------------------------
# 11. Obtener opción
# ------------------------------------------------------------------

def get_bp_option_by_id(option_id: str) -> dict:
  db = SessionLocal()

  try:
    option = (
      db.query(BPOptionsModel)
      .filter(
        BPOptionsModel.id == option_id
      )
      .first()
    )

    if not option:
      return {
        "error": (
          f"Opción con ID '{option_id}' "
          "no fue encontrada."
        )
      }

    return {
      "id": option.id,
      "process_id": option.background_processes_id,
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

  finally:
    db.close()


# ------------------------------------------------------------------
# 12. Actualizar valores de opción
# ------------------------------------------------------------------

def update_bp_option_values(
  option_id: str,
  values: list
) -> dict:

  db = SessionLocal()

  try:
    option = (
      db.query(BPOptionsModel)
      .filter(
        BPOptionsModel.id == option_id
      )
      .first()
    )

    if not option:
      return {
        "error": (
          f"Opción con ID '{option_id}' "
          "no fue encontrada."
        )
      }

    if not isinstance(values, list):
      return {
        "error": (
          "Los valores deben enviarse "
          "como una lista."
        )
      }

    if not option.multiple and len(values) > 1:
      return {
        "error": (
          "Esta opción solo permite "
          "un valor."
        )
      }

    for value in values:
      if value is None:
        return {
          "error": (
            "Los valores no pueden ser null."
          )
        }

      if not isinstance(value, str):
        value = str(value)

      if len(value) > 500:
        return {
          "error": (
            "Un valor supera los 500 caracteres."
          )
        }

    option.values.clear()

    for value in values:
      option.values.append(
        BPOptionValueModel(
          value=value
        )
      )

    db.commit()
    db.refresh(option)

    return {
      "id": option.id,
      "key": option.key,
      "multiple": option.multiple,
      "values": [
        {
          "id": item.id,
          "value": item.value
        }
        for item in option.values
      ],
      "message": (
        "Valores actualizados correctamente."
      )
    }

  except Exception as e:
    db.rollback()
    return {
      "error": (
        f"Error al actualizar la opción: "
        f"{str(e)}"
      )
    }
  finally:
    db.close()
