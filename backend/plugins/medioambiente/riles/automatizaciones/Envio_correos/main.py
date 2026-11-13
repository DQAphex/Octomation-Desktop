import sys
from pathlib import Path
import httpx
from jinja2 import Template
import win32com.client as win32
import premailer
import base64
import os
import tempfile
from typing import List, Dict, Any, Optional
from ...riles_config import FILES_DIR
import traceback

CURRENT_DIR = Path(__file__).resolve().parent

from .envio_correos_config import FILE_TEMPLATE_DIR

BASE_URL = "/medioambiente/riles/api/v1"

def load_template():
  with open(FILE_TEMPLATE_DIR, 'r', encoding='utf-8') as template:
    return template.read()

def set_parameters(params):
  loaded_template_html = load_template()
  mail_template = Template(loaded_template_html)
  if isinstance(params, dict):
    filled_html = mail_template.render(**params)
  else:
    filled_html = mail_template.render(params)

  final_html = premailer.transform(filled_html)
  return final_html

def generate_mail(
      recipients: List[str], subject: str, params: dict
  ) -> str:
    """Envía el correo mediante Outlook a una lista de destinatarios."""
    print("FUCK")
    if not recipients:
      return "No hay destinatarios configurados para este envío."
    
    temp_file_path = None
    try:
      print("[1] 45")
      outlook = win32.Dispatch("outlook.application")
      mail = outlook.CreateItem(0)
      # Agregar múltiples destinatarios separados por punto y coma
      mail.To = "; ".join(recipients)
      mail.Subject = subject
      mail.HTMLBody = set_parameters(params)

      # Adjuntar PDF desde Base64
      # Adjuntar PDF desde FILES_DIR
      analysis_id = params.get("analysis_id")
      fecha_muestreo = params.get("fecha_muestreo")
      local_id = params.get("local_id")
      print("[2]",analysis_id,fecha_muestreo,local_id)
      if analysis_id and fecha_muestreo and local_id:
        yyyymm = fecha_muestreo.strftime("%Y%m")

        nombre_archivo = f"{analysis_id}_{yyyymm}_{local_id}.pdf"
        print(FILES_DIR / nombre_archivo)
        file_path = FILES_DIR / nombre_archivo

        if file_path.exists():
          mail.Attachments.Add(str(file_path))
          print(f"PDF adjuntado: {file_path}")
        else:
          print(f"No se encontró el PDF: {file_path}")

      mail.Send()
      return "Enviado con éxito"

    except Exception as e:
      traceback.print_exc()
      return f"Error al enviar correo: {str(e)}"

    finally:
      if temp_file_path and os.path.exists(temp_file_path):
        try:
          os.remove(temp_file_path)
        except Exception:
          pass


def run(data: dict, recipients: List[str],type:str='local') :
  print("run", end="\n")
  if not data:
    print("No se recibieron datos para generar el correo.")

  if type == 'local':
    # subject = f"RPM N° {data.get('local_rpm','').split('.')[0]} UNIMARC {data.get('local_nombre', '')} DE MES {data.get('fecha_muestreo', '').strftime('%m/%Y') if data.get('fecha_muestreo') else ''}"
    subject = f"Analisis de Riles - Local: {data.get('local_nombre', '')} - CECO: {data.get('local_id', '')}"
  else:
    subject = f"RPM N° {data.get('local_rpm','').split('.')[0]} UNIMARC {data.get('local_nombre', '')} DE MES {data.get('fecha_muestreo', '').strftime('%m/%Y') if data.get('fecha_muestreo') else ''}"

  resultado = generate_mail(recipients, subject, data)



def testing():
  """Procesa toda la cola de correos obteniendo las IDs y ejecutando run()"""
  with httpx.Client(base_url=BASE_URL) as client:
    request_get_maling_queue = client.get("/get-mailing-queue")
    
    if request_get_maling_queue.status_code != 200:
      print("Error al obtener la cola de envíos")
      return

    response_get_maling_queue = request_get_maling_queue.json()
    
    for item in response_get_maling_queue:
      analysis_id = int(item["id"])
      run(analysis_id, to="dquioza@smu.cl")

if __name__ == "__main__":
  testing()