import enum
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Numeric, ForeignKey, Enum,Unicode
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, Any
from decimal import Decimal

from .database import Base


class PDFDataModel(Base):
  __tablename__ = "pdf_records"

  id = Column(Integer, primary_key=True, index=True)
  name_archivo = Column(String(255), nullable=False)
  datos_extra = Column(Text, nullable=True)
  created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AnalisisAguaModel(Base):
  __tablename__ = "analisis_agua"

  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  empresa = Column(String(255), nullable=True)
  local_id = Column(String(100), nullable=True)
  local_nombre = Column(String(255), nullable=True)
  local_region = Column(String(255), nullable=True)
  local_comuna = Column(String(255), nullable=True)
  local_direccion = Column(String(255), nullable=True)
  local_rpm = Column(String(100), nullable=True)
  local_convenio = Column(String(100), nullable=True)
  laboratorio = Column(String(255), nullable=True)
  fecha_emision = Column(DateTime, nullable=True)
  fecha_muestreo = Column(DateTime, nullable=True)
  tipo_muestreo = Column(String(100), nullable=True)
  tipo_monitoreo = Column(String(30), nullable=True)
  aceites_grasas = Column(String(100), nullable=True)
  ph = Column(String(100), nullable=True)
  dbo5 = Column(String(100), nullable=True)
  dqo = Column(String(100), nullable=True)
  fosforo = Column(String(100), nullable=True)
  nitrogeno_amoniacal = Column(String(100), nullable=True)
  poder_espumogeno = Column(String(100), nullable=True)
  solidos_sedimentables = Column(String(100), nullable=True)
  solidos_suspendidos_totales = Column(String(100), nullable=True)
  volumen_de_descarga_diaria = Column(String(100), nullable=True)
  volumen_de_descarga_mensual = Column(String(100), nullable=True)
  aluminio = Column(String(100), nullable=True)
  arsenico = Column(String(100), nullable=True)
  boro = Column(String(100), nullable=True)
  cadmio = Column(String(100), nullable=True)
  cianuro = Column(String(100), nullable=True)
  zinc = Column(String(100), nullable=True)
  cobre = Column(String(100), nullable=True)
  cromo_total = Column(String(100), nullable=True)
  cromo_hexavalente = Column(String(100), nullable=True)
  hidrocarburos_totales = Column(String(100), nullable=True)
  manganeso = Column(String(100), nullable=True)
  mercurio = Column(String(100), nullable=True)
  niquel = Column(String(100), nullable=True)
  plomo = Column(String(100), nullable=True)
  sulfatos = Column(String(100), nullable=True)
  sulfuros = Column(String(100), nullable=True)
  temperatura=Column(String(100), nullable=True)
  created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PDFInboxModel(Base):
  __tablename__ = "pdf_inbox"

  id_inbox = Column("id", Integer, primary_key=True, index=True)
  id_correo = Column(String(255), nullable=False)
  id_file = Column(String(14), nullable=False)
  parameters = Column(
      JSON, nullable=False
  )  # Acepta diccionarios/listas de Python directamente
  is_active = Column(Boolean, default=False, nullable=False)

class ParametroModel(Base):
  __tablename__ = "parametros"

  id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  parametro: Mapped[str] = mapped_column(String(255), nullable=False)
  unidad: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
  expresion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
  maximo: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
  tolerancia_minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
  tolerancia_maximo: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

class EvaluacionParametrosModel(Base):
  __tablename__ = "evaluacion_parametros"

  id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  id_analisis: Mapped[int] = mapped_column(ForeignKey("analisis_agua.id"), unique=True)

  aceites_grasas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  aluminio: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  arsenico: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  boro: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  cadmio: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  cianuro: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  cobre: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  cromo_hexavalente: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  cromo_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  hidrocarburos_totales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  manganeso: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  mercurio: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  niquel: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  ph: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  plomo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  poder_espumogeno: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  solidos_sedimentables: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  sulfatos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  sulfuros: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  zinc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  dbo5: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  fosforo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  nitrogeno_amoniacal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  solidos_suspendidos_totales: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
  dqo:Mapped[Optional[int]] = mapped_column(Integer,nullable=True)

MAPEO_NOMBRES_COLUMNAS = {
  "Aceites y Grasas": "aceites_grasas",
  "Aluminio": "aluminio",
  "Arsénico": "arsenico",
  "Boro": "boro",
  "Cadmio": "cadmio",
  "Cianuro": "cianuro",
  "Cobre": "cobre",
  "Cromo Hexavalente": "cromo_hexavalente",
  "Cromo Total": "cromo_total",
  "Hidrocarburos Totales": "hidrocarburos_totales",
  "Manganeso": "manganeso",
  "Mercurio": "mercurio",
  "Niquel": "niquel",
  "pH": "ph",
  "Plomo": "plomo",
  "Poder Espumógeno": "poder_espumogeno",
  "S. Sedimentables": "solidos_sedimentables",
  "Sulfatos": "sulfatos",
  "Sulfuros": "sulfuros",
  "Zinc": "zinc",
  "DBO5": "dbo5",
  "Fosforo": "fosforo",
  "Nitrogeno Amoniacal": "nitrogeno_amoniacal",
  "Solidos Suspendidos Totales": "solidos_suspendidos_totales"
}

def parse_float_val(value: Any) -> Optional[float]:
  if value is None:
    return None
  if isinstance(value, (int, float, Decimal)):
    return float(value)
  if isinstance(value, str):
    val_str = value.strip().replace(",", ".")
    if not val_str:
      return None
    try:
      return float(val_str)
    except ValueError:
      return None
  return None

def calcular_estado_parametro(valor: float, regla: ParametroModel) -> int:
  limite_max = float(regla.maximo) if regla.maximo is not None else float("inf")
  limite_min = float(regla.minimo) if regla.minimo is not None else 0.0
  tol_max = float(regla.tolerancia_maximo) if regla.tolerancia_maximo is not None else 1.0
  tol_min = float(regla.tolerancia_minimo) if regla.tolerancia_minimo is not None else 1.0

  ratio_max = limite_max * tol_max
  ratio_min = limite_min / tol_min if tol_min > 0 else 0.0

  if valor > ratio_max or valor < ratio_min:
    return 2

  if valor > limite_max or valor < limite_min:
    return 1

  return 0



class MailingStatus(str, enum.Enum):
  PENDIENTE = "PENDIENTE"
  ENVIADO = "ENVIADO"
  ERROR = "ERROR"

# 2. Modelo con el campo Enum
class MailingModel(Base):
    __tablename__ = "mailing"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    id_analisis: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False
    )

    status_local: Mapped[MailingStatus] = mapped_column(
        Enum(MailingStatus),
        default=MailingStatus.PENDIENTE
    )

    status_sanitaria: Mapped[MailingStatus] = mapped_column(
        Enum(MailingStatus),
        default=MailingStatus.PENDIENTE
    )

class File_b64_Model(Base):
    __tablename__ = "File_64_storage"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    id_analisis: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False
    )

    b64: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

class EstadoConvenio(str, enum.Enum):
  SIN_CONVENIO = "SIN CONVENIO"
  CONVENIO = "CONVENIO"
  TERMINADO = "TERMINADO"
  ERROR = "error"

class Formato(str, enum.Enum):
  UNI = "UNI"
  M10 = "M10"
  ALVI = "ALVI"
  OFICINAS = "OFICINAS"
  ERROR = "error"


class StoreModule(Base):
  __tablename__ = "locales"

  id_local: Mapped[str] = mapped_column(String, primary_key=True)
  dirreccion: Mapped[str] = mapped_column(Unicode, nullable=False)
  nombre: Mapped[str] = mapped_column(Unicode, nullable=False)
  region: Mapped[str] = mapped_column(Unicode, nullable=False)
  comuna: Mapped[str] = mapped_column(Unicode, nullable=False)
  rpm: Mapped[int] = mapped_column(Integer, nullable=False)
  # CORREGIDO: Se cambia Integer por Unicode
  empresa_distribuidora: Mapped[str] = mapped_column(Unicode, nullable=False)
  formato: Mapped[Formato] = mapped_column(
    Enum(Formato), default=Formato.UNI, nullable=False
  )
  convenio: Mapped[EstadoConvenio] = mapped_column(
    Enum(EstadoConvenio), default=EstadoConvenio.SIN_CONVENIO, nullable=False
  )
  
class LocalMailModel(Base):
  __tablename__ = "local_mail"

  # Única clave primaria sustituta (Autoincremental)
  id_local_mail: Mapped[int] = mapped_column(
      Integer, primary_key=True, autoincrement=True
  )

  # Clave foránea / Identificador del local (No debe llevar primary_key=True)
  id_local: Mapped[str] = mapped_column(String(20), nullable=False)
  mail: Mapped[str] = mapped_column(String(100), nullable=False)
  mail_type: Mapped[str] = mapped_column(String(20), nullable=False)