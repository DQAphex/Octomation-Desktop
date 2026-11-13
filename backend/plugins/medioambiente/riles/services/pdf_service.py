# services/pdf_service.py
import base64
import io
from typing import List, Tuple, Dict, Any
from fastapi import UploadFile, HTTPException, status
import pandas as pd

from ..automatizaciones.lectorPdf.main import (
  export_analysis_to_json,
  process_pdf_bytes,
)


class PDFService:
  @staticmethod
  async def process_single_pdf(file: UploadFile) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo proporcionado no es un PDF válido.",
      )

    file_bytes = await file.read()
    result = process_pdf_bytes(file_bytes=file_bytes, filename=file.filename)

    if not result:
      raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
          "No se pudo identificar el laboratorio o procesar el archivo"
          f" '{file.filename}'."
        ),
      )

    return {"status": "exito", "data": result}

  @staticmethod
  async def process_multiple_pdfs(files: List[UploadFile]) -> Dict[str, Any]:
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

  @staticmethod
  async def parse_parameters_file(file: UploadFile) -> List[Dict[str, Any]]:
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".csv")):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo debe ser formato .xlsx o .csv",
      )

    contents = await file.read()

    if file.filename.endswith(".xlsx"):
      df = pd.read_excel(io.BytesIO(contents))
    else:
      df = pd.read_csv(io.BytesIO(contents))

    df.columns = df.columns.str.strip()

    column_mapping = {
      "Parámetro": "parametro",
      "Unidad": "unidad",
      "Expresión": "expresion",
      "Mínimo": "minimo",
      "Maximo": "maximo",
      "Tolerancia Mínimo (-)": "tolerancia_minimo",
      "Tolerancia Maximo (+)": "tolerancia_maximo",
    }

    df = df.rename(columns=column_mapping)

    numeric_cols = [
      "minimo",
      "maximo",
      "tolerancia_minimo",
      "tolerancia_maximo",
    ]

    for col in numeric_cols:
      if col in df.columns:
        df[col] = df[col].astype(str).str.replace(",", ".").str.strip()
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.where(pd.notnull(df), None)
    return df.to_dict(orient="records")