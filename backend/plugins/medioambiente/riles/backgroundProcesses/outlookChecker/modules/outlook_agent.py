import os
import pythoncom
import requests
import win32com.client
from plyer import notification
from datetime import datetime, timedelta
import uuid

PROCESS_MULTIPLE_PDFS_ENDPOINT = (
    "http://localhost:8000/medioambiente/riles/api/v1/process-multiple-pdfs"
)
SET_INBOX_ENDPOINT = (
    "http://localhost:8000/medioambiente/riles/api/v1/set-inbox-params"
)
GET_DEACTIVATED_IDS_ENDPOINT = (
    "http://localhost:8000/medioambiente/riles/api/v1/get-deactivated-inbox"
)
GET_OPENED_IDS_ENDPOINT = (
    "http://localhost:8000/medioambiente/riles/api/v1/get-opened-inbox"
)

def notificar_windows(titulo: str, mensaje: str) -> None:
  """Muestra una notificación nativa en el escritorio de Windows."""
  try:
    notification.notify(
        title=titulo,
        message=mensaje,
        app_name="Outlook PDF Checker",
        timeout=5,
    )
  except Exception as e:
    print(f"Error al enviar notificación: {e}")


def guardar_parametros_inbox(
    registros_api, id_correo_origen="OUTLOOK_DEFAULT"
):
  """Consume el endpoint /api/v1/set-inbox-params para guardar los registros."""
  payload = []
  for item in registros_api:
    id = uuid.uuid4()
    dto = {
        "id_correo": str(id_correo_origen),
        "id_file": str(id),
        "parameters": item,
        "is_active": True,
    }
    payload.append(dto)

  if not payload:
    return

  try:
    response = requests.post(
        SET_INBOX_ENDPOINT, json=payload, timeout=30
    )

    if response.status_code == 201:
      print(
          f"  -> Persistido en BD exitosamente: {response.json().get('message')}"
      )
    else:
      print(
          f"  -> Error al guardar en BD ({response.status_code}):"
          f" {response.text}"
      )
  except Exception as e:
    print(f"  -> Error de conexión al guardar en BD: {e}")


def obtener_correos_inactivos():
  """Obtiene la lista de id_correo desactivados desde la API."""
  try:
    response = requests.get(GET_DEACTIVATED_IDS_ENDPOINT, timeout=15)
    if response.status_code == 200:
      return set(response.json())
    return set()
  except Exception as e:
    print(f"Error al obtener correos inactivos: {e}")
    return set()

def obtener_correos_leidos():
  """Obtiene la lista de id_correo desactivados desde la API."""
  try:
    response = requests.get(GET_OPENED_IDS_ENDPOINT, timeout=15)
    if response.status_code == 200:
      return set(response.json())
    return set()
  except Exception as e:
    print(f"Error al obtener correos inactivos: {e}")
    return set()

def descargar_adjuntos():
  notificar_windows(
    "Outlook Agent Activo",
    "El programa está buscando correos con adjuntos PDF.",
  )

  pythoncom.CoInitialize()

  try:
    outlook = win32com.client.Dispatch(
      "Outlook.Application"
    ).GetNamespace("MAPI")

    inbox = outlook.GetDefaultFolder(6)

    # ========================================
    # FILTRO DE FECHAS
    # ========================================

    ahora = datetime.now()

    fecha_desde = datetime(
      ahora.year,
      ahora.month,
      ahora.day
    ) - timedelta(days=1)

    print("========================================")
    print(f"datetime.now(): {ahora}")
    print(f"fecha_desde:    {fecha_desde}")
    print("========================================")

    filter_str = (
      '@SQL="urn:schemas:httpmail:hasattachment" = 1'
    )

    filtered_messages = inbox.Items.Restrict(filter_str)

    # Importante:
    # Outlook puede devolver los correos desordenados.
    # Ordenamos del más reciente al más antiguo.
    filtered_messages.Sort(
      "[ReceivedTime]",
      True
    )

    correos_leidos = obtener_correos_leidos()

    PR_ATTACH_DATA_BIN = (
      "http://schemas.microsoft.com/mapi/proptag/0x37010102"
    )

    for message in list(filtered_messages):
      try:
        received_time = message.ReceivedTime

        # ========================================
        # NORMALIZAR FECHA DE OUTLOOK
        # ========================================

        if received_time.tzinfo is not None:
          received_time = received_time.replace(
            tzinfo=None
          )

        print(
          f"Correo: {message.Subject} | "
          f"ReceivedTime: {received_time}"
        )

        # ========================================
        # CORTE POR FECHA
        # ========================================

        if received_time < fecha_desde:
          print(
            "⏹ Correo anterior al límite. "
            "Deteniendo búsqueda."
          )
          break

        entry_id = message.EntryID

        if entry_id in correos_leidos:
          print(
            f"correo inactivo: {entry_id}"
          )
          continue

        print(
          f"Procesando correo: {message.Subject}"
        )

        files_payload = []

        for attachment in message.Attachments:
          if attachment.FileName.lower().endswith(".pdf"):
            raw_data = (
              attachment.PropertyAccessor.GetProperty(
                PR_ATTACH_DATA_BIN
              )
            )

            pdf_bytes = bytes(raw_data)

            files_payload.append(
              (
                "files",
                (
                  attachment.FileName,
                  pdf_bytes,
                  "application/pdf"
                ),
              )
            )

        if files_payload:
          response = requests.post(
            PROCESS_MULTIPLE_PDFS_ENDPOINT,
            files=files_payload,
            timeout=120,
          )

          if response.status_code == 200:
            res = response.json()

            registros = res.get(
              "data",
              []
            )

            guardar_parametros_inbox(
              registros,
              id_correo_origen=entry_id
            )

          else:
            print(
              f"  - Error en la API "
              f"({response.status_code}): "
              f"{response.text}"
            )

      except Exception as e:
        print(
          f"Error procesando mensaje individual: {e}"
        )

  except Exception as e:
    print(
      f"Error general en el agente de Outlook: {e}"
    )

  finally:
    pythoncom.CoUninitialize()