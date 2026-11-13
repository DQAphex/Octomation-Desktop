from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from ..riles_config import DB_DIR

# 1. Crear el directorio físicamente si no existe
DB_DIR.mkdir(parents=True, exist_ok=True)

# 2. Definir la ruta del archivo
DB_PATH = DB_DIR / "riles_data.db"

# 3. String de conexión seguro para Windows y SQLite
DATABASE_URL = f"sqlite:///{DB_PATH.resolve().as_posix()}"

engine = create_engine(
  DATABASE_URL,
  connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
  cursor = dbapi_connection.cursor()
  cursor.execute("PRAGMA foreign_keys=ON")
  cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()