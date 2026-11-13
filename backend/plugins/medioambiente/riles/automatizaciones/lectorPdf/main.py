import base64
from datetime import datetime
import os
from pathlib import Path
import sys
from typing import List, Optional

from fastapi import File, HTTPException, UploadFile, status
import fitz  # PyMuPDF
import pandas as pd

# Obtener la carpeta donde vive este worker.py
CURRENT_DIR = Path(__file__).resolve().parent

# Forzar a Python a buscar PRIMERO en la carpeta local de este worker
if str(CURRENT_DIR) not in sys.path:
  sys.path.insert(0, str(CURRENT_DIR))

# Obtener la fecha y hora actual en formato yymmddhhmmss
tiempo_actual = datetime.now().strftime("%y%m%d%H%M%S")

# Importar tus readers
from utils.dtos import AnalisisAguaDTO
from readers.agq_reader import agq_reader
from readers.anam_reader import anam_reader
from readers.ap_reader import ap_reader
from readers.biodiversaReader import biodiversa_reader
from readers.hidrolab_reader import hidrolab_reader
from readers.merieux_reader import merieux_reader, merieux_reader_string
from readers.sgs_reader import sgs_reader

# Configuración centralizada de laboratorios y palabras clave
LAB_CONFIG = {
  "merieux": {
    "name": "merieux",
    "reader": [merieux_reader, merieux_reader_string, anam_reader],
    "use_lab": True,
    "lab": ["Food","MÉRIEUX","NUTRISCIENCES"],
  },
  "hidrolab": {
    "name": "hidrolab",
    "reader": [hidrolab_reader],
    "use_lab": False,
    "lab": "www.hidrolab.com",
  },
  "anam": {
    "name": "anam",
    "reader": [anam_reader],
    "use_lab": False,
    "lab": "anam",
  },
  "sgs": {
    "name": "sgs",
    "reader": [sgs_reader],
    "use_lab": True,
    "lab": "société",
  },
  "biodiversa": {
    "name": "biodiversa",
    "reader": [biodiversa_reader],
    "use_lab": True,
    "lab": "biodiversa",
  },
  "aguas_patagonia": {
    "name": "aguas_patagonia",
    "reader": [ap_reader],
    "use_lab": False,
    "lab": "patagonia",
  },
  "agq": {
    "name": "agq",
    "reader": [agq_reader],
    "use_lab": False,
    "lab": "agq",
  },
}

CURRENT_TIME = datetime.now().strftime("%y%m%d%H%M%S")

def get_unrecognized_row(
    filename: str, lab_name: str = "desconocido"
) -> dict:
  """Genera el diccionario base con todos los parámetros inicializados en None mediante AnalisisAguaDTO."""
  dto = AnalisisAguaDTO(laboratorio=lab_name)
  data = dto.to_dict()
  data["name_archivo"] = filename
  return data


def process_pdf_bytes(file_bytes: bytes, filename: str = "documento.pdf") -> Optional[dict]:
  """
  Procesa los bytes de un archivo PDF, identifica el laboratorio y aplica el reader correspondiente.
  Retorna un diccionario con los datos procesados o None si falla/no coincide.
  """
  try:
    complete_text = ""

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
      for page in doc:
        t = page.get_text()
        if t:
          complete_text += t.lower() + "\n"

    for lab_name, config in LAB_CONFIG.items():
      keywords = config["lab"]

      if not isinstance(keywords, list):
        keywords = [keywords]

      keywords = [
        keyword.lower()
        for keyword in keywords
        if keyword
      ]

      print(f"\n🔎 Buscando laboratorio: {lab_name}")

      keyword_found = None

      for keyword in keywords:
        if keyword in complete_text:
          print(f"  ✅ Keyword encontrada: '{keyword}'")
          keyword_found = keyword
        else:
          print(f"  ❌ Keyword NO encontrada: '{keyword}'")

      if keyword_found:
        print(
          f"  🏷️ Laboratorio identificado: {lab_name} "
          f"(keyword: '{keyword_found}')"
        )

        readers = config["reader"]

        if not isinstance(readers, list):
          readers = [readers]

        result_dto = None

        for fn_reader in readers:
          try:
            if config["use_lab"]:
              res = fn_reader(file_bytes, config["name"])
            else:
              res = fn_reader(file_bytes)

            if isinstance(res, dict) and len(res) > 0:
              result_dto = res
              break
          except Exception as reader_err:
            print(
              f" -> Reader {fn_reader.__name__} falló: {reader_err}"
            )
            continue

        if isinstance(result_dto, dict):
          row_data = {
            "laboratorio": lab_name,
            "name_archivo": filename,
          }
          row_data.update(result_dto)
          return row_data

    print(f"❌ No se encontró ninguna keyword para: {filename}")

    return get_unrecognized_row(
      filename,
      lab_name="desconocido"
    )

  except Exception as e:
    print(f"Error al procesar el archivo {filename}: {e}")
    return None


def export_analysis_to_json(files_data: List[tuple]) -> dict:
  """
  Recibe una lista de tuplas (bytes, nombre_archivo, pdf_base64),
  los procesa y asigna la clave 'base64' al diccionario resultante.
  """
  records = []
  total_pdfs = len(files_data)

  for item in files_data:
    file_bytes = item[0]
    filename = item[1]
    pdf_b64 = item[2] if len(item) > 2 else None

    res = process_pdf_bytes(file_bytes, filename)
    if res:
      if pdf_b64:
        res["base64"] = pdf_b64
      records.append(res)

  return {
    "status": "completado",
    "total_pdfs": total_pdfs,
    "reportes_exitosos": len(records),
    "data": records,
  }


async def process_single_pdf(file: UploadFile = File(...)):
  """
  Recibe un archivo PDF, valida su formato, procesa el contenido
  y retorna los datos extraídos según el laboratorio identificado.
  """
  if not file.filename.lower().endswith(".pdf"):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="El archivo proporcionado no es un PDF válido.",
    )

  file_bytes = await file.read()
  pdf_base64 = base64.b64encode(file_bytes).decode("utf-8")
  result = process_pdf_bytes(file_bytes=file_bytes, filename=file.filename)

  if not result:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail=f"No se pudo identificar el laboratorio o procesar el archivo '{file.filename}'.",
    )

  result["base64"] = pdf_base64
  return {"status": "exito", "data": result}


async def process_multiple_pdfs(files: List[UploadFile] = File(...)):
  if not files:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Debes adjuntar al menos un archivo PDF.",
    )

  files_data = []
  for file in files:
    if file.filename and file.filename.lower().endswith(".pdf"):
      try:
        content = await file.read()
        pdf_base64 = base64.b64encode(content).decode("utf-8")
        files_data.append((content, file.filename, pdf_base64))
      finally:
        await file.close()

  if not files_data:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Ninguno de los archivos adjuntos es un PDF válido.",
    )

  response = export_analysis_to_json(files_data)
  return response