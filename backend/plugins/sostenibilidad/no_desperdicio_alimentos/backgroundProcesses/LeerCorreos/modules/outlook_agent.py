import os
import re
from datetime import datetime, timedelta
import pythoncom
import pymupdf
import win32com.client
import json
from outlook_config import METADATA_DIR
from paths import DB_DIR
from sqlalchemy import create_engine, text
import tempfile
from .file_rutine import File_Runtime
from .saveExcel import ExcelFile

def get_bp_id(): 
  with open(METADATA_DIR, "r", encoding="utf-8") as metadata:
    datos = json.load(metadata)
  id = datos["id"]
  return id

def getFunctionalData():
  engine = create_engine(
    f"sqlite:///{(DB_DIR / 'processes_registry.db').as_posix()}"
  )

  def getValues(engine, option):
    with engine.connect() as connection:
      result = connection.execute(
        text("""
          SELECT value
          FROM bp_option_values
          WHERE option_id = :option_id
        """),
        {"option_id": option}
      )
      return [row[0] for row in result]

  bp_id = get_bp_id()
  q_co = f"{bp_id}.carpetas_a_revisar"
  q_cd = f"{bp_id}.carpetas_de_destino"

  carpetas_outlook = getValues(engine, q_co)
  carpetas_destino = getValues(engine, q_cd)

  return carpetas_outlook, carpetas_destino

CARPETA_OUTLOOK = "Red de alimentos"

CARPETA_DESTINO : str = (
  r"C:\Users\dquioza\OneDrive - SMU S.A"
  r"\Escritorio\test"
)


def leer_pdf(pdf_bytes: bytes) -> str:
  with pymupdf.open(
    stream=pdf_bytes,
    filetype="pdf"
  ) as pdf:
    return "".join(
      pagina.get_text()
      for pagina in pdf
    )


def obtener_folio(texto: str) -> str | None:
  patron = (
    r"N[º°]\s*FOLIO\s*:\s*"
    r"(?:\n\s*)?"
    r"N?[º°]?\s*(\d+)"
  )

  resultado = re.search(
    patron,
    texto,
    re.IGNORECASE
  )

  if resultado:
    return resultado.group(1)

  return None


def generar_nombre_archivo(folio: str) -> str:
  folio_formateado = f"{int(folio):05d}"

  return f"FOLIO_N_{folio_formateado}.pdf"


def procesar_correos():
  carpetas_outlook, carpetas_destino = getFunctionalData()
  print(carpetas_outlook, carpetas_destino)

  pythoncom.CoInitialize()
  try:
    cantidad_pdf = 0
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")
    inbox = namespace.GetDefaultFolder(6)

    fecha_desde = (
      datetime.now() - timedelta(days=2)
    ).replace(
      hour=0,
      minute=0,
      second=0,
      microsecond=0
    )

    for nombre_carpeta in carpetas_outlook:
      carpeta_destino = carpetas_destino[0]

      try:
        carpeta = inbox.Folders[nombre_carpeta]
      except Exception:
        print(
          f"❌ No se encontró la carpeta "
          f"'{nombre_carpeta}'"
        )
        continue

      print(
        f"✓ Carpeta encontrada: {nombre_carpeta}"
      )
      print(
        f"✓ Destino: {carpeta_destino}"
      )

      os.makedirs(
        carpeta_destino,
        exist_ok=True
      )

      items = carpeta.Items
      items.Sort("[ReceivedTime]", True)

      for message in items:
        try:
          recibido = message.ReceivedTime

          print(
            f"Correo: {message.Subject} | "
            f"ReceivedTime: {recibido}"
          )

          if recibido.tzinfo is not None:
            recibido = recibido.replace(
              tzinfo=None
            )

          if recibido < fecha_desde:
            print(
              "⏹ Correo anterior al límite. "
              "Deteniendo búsqueda."
            )
            break

          print(
            f"Procesando correo: {message.Subject}"
          )

          if message.Attachments.Count == 0:
            continue

          for attachment in message.Attachments:
            try:
              nombre_original = attachment.FileName

              if not nombre_original.lower().endswith(".pdf"):
                continue

              print(
                f"  PDF encontrado: "
                f"{nombre_original}"
              )

              with tempfile.NamedTemporaryFile(
                  suffix=".pdf",
                  delete=False
                ) as temp:
                  temp_path = temp.name

              try:
                attachment.SaveAsFile(temp_path)

                with open(temp_path, "rb") as archivo:
                  pdf_bytes = archivo.read()

                texto = leer_pdf(pdf_bytes)
                fr = File_Runtime(pdf_bytes=pdf_bytes)
                fr.orchestrator_extract_data()

                excel_guias = ExcelFile(file_path=carpetas_destino[0])
                excel_guias.export_to_excel(table=fr.excel_export)
                
                folio = fr.folio

              finally:
                if os.path.exists(temp_path):
                  os.remove(temp_path)

              if not folio:
                print(
                  "  ⚠ No se encontró el folio."
                )
                continue

              print(
                f"  ✓ Folio encontrado: {folio}"
              )

              nombre_archivo = (
                generar_nombre_archivo(folio)
              )

              ruta_destino = os.path.join(
                carpeta_destino,
                nombre_archivo
              )

              if os.path.exists(ruta_destino):
                print(
                  f"  ⚠ El archivo ya existe: "
                  f"{nombre_archivo}"
                )
                continue

              attachment.SaveAsFile(
                ruta_destino
              )

              print(
                f"  ✓ Guardado en: "
                f"{ruta_destino}"
              )

              cantidad_pdf += 1

            except Exception as e:
              print(
                f"  ❌ Error procesando adjunto "
                f"'{attachment.FileName}': {e}"
              )

          print()

        except Exception as e:
          print(
            f"❌ Error procesando correo "
            f"'{message.Subject}': {e}"
          )

    print(
      "========================================"
    )
    print(
      f"✓ Proceso terminado. "
      f"PDF descargados: {cantidad_pdf}"
    )
    print(
      "========================================"
    )

  finally:
    pythoncom.CoUninitialize()


if __name__ == "__main__":
  procesar_correos()