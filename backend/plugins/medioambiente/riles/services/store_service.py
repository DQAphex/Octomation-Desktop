from typing import List
from fastapi import UploadFile, HTTPException, status
from io import BytesIO,TextIOWrapper
import pandas as pd
from io import StringIO
from sqlalchemy.orm import Session
from sqlalchemy import asc, func
import csv
from fastapi.responses import StreamingResponse

from .models import (
  StoreModule,
  AnalisisAguaModel,
  EstadoConvenio,
  Formato

)

class StoreService:
  @staticmethod
  async def set_stores(
    file: UploadFile, db: Session
  ) -> List[StoreModule]:
    if not file.filename.endswith(".csv"):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo debe ser un CSV.",
      )

    content = await file.read()

    # Intentar decodificar en UTF-8 con BOM y fallback a Latin-1 (Excel Windows)
    try:
      decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
      decoded_content = content.decode("latin-1")

    buffer = StringIO(decoded_content)
    reader = csv.DictReader(buffer, delimiter=";")

    nuevos_locales = []
    db.query(StoreModule).delete()

    for row in reader:
      # Limpiar claves del diccionario para evitar diferencias de casing o espacios
      clean_row = {
        key.strip().upper(): value.strip() if value else ""
        for key, value in row.items()
        if key
      }

      id_local_val = clean_row.get("ID_LOCAL", "")

      try:
        rpm_val = int(clean_row.get("RPM", 0))
      except ValueError:
        rpm_val = 0

      raw_convenio = clean_row.get("CONVENIO", "")
      try:
        convenio_val = EstadoConvenio(raw_convenio)
      except ValueError:
        convenio_val = EstadoConvenio.ERROR

      raw_formato = clean_row.get("FORMATO", "")
      try:
        formato_val = Formato(raw_formato)
      except ValueError:
        formato_val = Formato.ERROR

      local = StoreModule(
        id_local=id_local_val,
        dirreccion=clean_row.get("DIRECCIÓN", clean_row.get("DIRECCION", "")),
        nombre=clean_row.get("LOCAL", ""),
        region=clean_row.get("REGIÓN", clean_row.get("REGION", "")),
        comuna=clean_row.get("COMUNA", ""),
        rpm=rpm_val,
        empresa_distribuidora=clean_row.get("EMPRESA DISTRIBUIDORA", ""),
        formato=formato_val,
        convenio=convenio_val,
      )

      db.add(local)
      nuevos_locales.append(local)

    db.commit()
    return nuevos_locales

  @staticmethod
  async def export_stores_csv(db: Session) -> StreamingResponse:
    locales = db.query(StoreModule).all()

    # 1. Crear un buffer de bytes
    bytes_buffer = BytesIO()

    # 2. Wrapper de texto con la codificación 'utf-8-sig' (agrega el BOM automáticamente)
    text_buffer = TextIOWrapper(
      bytes_buffer, encoding="utf-8-sig", newline=""
    )

    writer = csv.writer(text_buffer, delimiter=";")

    # 3. Escribir Encabezados
    writer.writerow([
      "ID_LOCAL",
      "DIRECCIÓN",
      "LOCAL",
      "REGIÓN",
      "COMUNA",
      "RPM",
      "EMPRESA DISTRIBUIDORA",
      "FORMATO",
      "CONVENIO",
    ])

    # 4. Escribir Registros
    for local in locales:
      writer.writerow([
        local.id_local,
        local.dirreccion,
        local.nombre,
        local.region,
        local.comuna,
        local.rpm,
        local.empresa_distribuidora,
        local.formato.value if local.formato else "",
        local.convenio.value if local.convenio else "",
      ])

    # 5. Volcar el buffer de texto al buffer de bytes sin cerrarlo
    text_buffer.flush()
    bytes_buffer.seek(0)

    headers = {
      "Content-Disposition": "attachment; filename=locales_exportados.csv"
    }

    # 6. Retornar el contenido de los bytes de forma limpia
    return StreamingResponse(
      iter([bytes_buffer.getvalue()]),
      media_type="text/csv; charset=utf-8",
      headers=headers,
    )
  @staticmethod
  async def get_stores(db: Session) -> List[dict]:
    locales = db.query(StoreModule).order_by(asc(StoreModule.id_local)).all()
    return locales
  
  @staticmethod
  async def get_stores_ids(db: Session) -> List[str]:
    locales = db.query(StoreModule.id_local).order_by(asc(StoreModule.id_local)).all()
    return [local.id_local for local in locales]
  
  @staticmethod
  async def get_stores_summarized(db: Session) -> List[dict]:
    locales = db.query(StoreModule.id_local, StoreModule.nombre).order_by(asc(StoreModule.id_local)).all()
    return [{"id_local":local.id_local,"local_nombre":local.nombre} for local in locales]


  @staticmethod
  async def get_stores_analysis(db: Session) -> List[dict]:
    locales = (
      db.query(
        StoreModule.id_local,
        StoreModule.nombre,
        func.count(AnalisisAguaModel.id).label("total_registros")
      )
      .join(AnalisisAguaModel, StoreModule.id_local == AnalisisAguaModel.local_id)
      .group_by(StoreModule.id_local, StoreModule.nombre)
      .order_by(asc(StoreModule.id_local))
      .all()
    )
    return [{"id_local":local.id_local,"local_nombre":local.nombre,"total_registros":local.total_registros} for local in locales]

  