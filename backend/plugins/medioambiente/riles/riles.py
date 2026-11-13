# plugins/medioambiente/riles/riles.py
import csv
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, Request, UploadFile, status, Body, Query,Path
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import io
from sqlalchemy.orm import Session

from paths import STATIC_DIR, TEMPLATES_DIR
from .riles_config import STATIC_DIR as R_STATIC_DIR, PAGES_DIR
from .services.database import Base, engine, get_db

from .services.schemas import (
  AnalisisAguaSchema,
  PDFInboxSchema,
  ParametroResponse,
  ParametroUpdate,
  File_b64_Schema,
  LocalMailBase,
  LocalMailSchema,
  StoreResponse
)

from .services.pdf_service import PDFService
from .services.riles_service import RilesService
from .services.inbox_service import InboxService
from .services.parameter_service import ParameterService
from .services.store_service import StoreService
from .services.transform_xlsx_service import ExcelTransformService
from .services.mails_service import LocalMailService

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/riles", tags=["Automatización de riles"])

templates = Jinja2Templates(directory=[PAGES_DIR, TEMPLATES_DIR])

# router.mount("/static", StaticFiles(directory=R_STATIC_DIR), name="static")
# router.mount("/static-global", StaticFiles(directory=STATIC_DIR), name="static_global")


@router.post( 
  "/api/v1/process-pdf",
  summary="Procesar un único PDF",
  status_code=status.HTTP_200_OK,
)
async def process_single_pdf(file: UploadFile = File(...)):
  return await PDFService.process_single_pdf(file)


@router.post(
  "/api/v1/process-multiple-pdfs",
  summary="Procesar múltiples archivos PDF",
  status_code=status.HTTP_200_OK,
  openapi_extra={
    "requestBody": {
      "content": {
        "multipart/form-data": {
          "schema": {
            "type": "object",
            "properties": {
              "files": {
                "type": "array",
                "items": {
                  "type": "string",
                  "format": "binary",
                },
                "description": "Lista de archivos PDF a procesar",
              }
            },
            "required": ["files"],
          }
        }
      }
    }
  },
)
async def process_multiple_pdfs(files: List[UploadFile] = File(...)):
  return await PDFService.process_multiple_pdfs(files)


@router.post("/api/v1/save-pdf-b64", status_code=status.HTTP_201_CREATED)
async def save_pdf_b64(
  payload: File_b64_Schema, db: Session = Depends(get_db)
) -> Dict[str, Any]:
  return RilesService.save_pdf_b64(payload, db)


@router.get(
  "/api/v1/download-pdf-b64/{id_analisis}", status_code=status.HTTP_200_OK
)
async def download_pdf_b64(id_analisis: int, db: Session = Depends(get_db)):
  return RilesService.download_pdf_b64(id_analisis, db)


@router.get("/api/v1/get-pdf-b64/{id_analisis}", status_code=status.HTTP_200_OK)
def get_pdf_b64(id_analisis: int, db: Session = Depends(get_db)) -> str:
  return RilesService.get_pdf_b64(id_analisis, db)

#====================================
# Analisis Resultados
#====================================


@router.get("/api/v1/get-pdf-data", status_code=status.HTTP_200_OK)
async def get_pdf_data(
  analysis_id: Optional[int] = None, db: Session = Depends(get_db)
):
  return RilesService.get_pdf_data(analysis_id, db)

@router.get("/api/v1/get-pdf-data-by-store", status_code=status.HTTP_200_OK)
async def get_pdf_data(
  store_id: Optional[int] = None, db: Session = Depends(get_db)
):
  return RilesService.get_pdf_data_by_store(store_id, db)


@router.post("/api/v1/save-pdf-data", status_code=status.HTTP_201_CREATED)
async def save_pdf_data(
  payload: List[AnalisisAguaSchema], db: Session = Depends(get_db)
):
  return RilesService.save_pdf_data(payload, db)


@router.delete("/api/v1/delete-pdf-data", status_code=status.HTTP_201_CREATED)
async def delete_pdf_data(db: Session = Depends(get_db)):
  return RilesService.delete_pdf_data(db)

@router.get("/api/v1/export-pdf-data", status_code=status.HTTP_200_OK)
async def export_pdf_data(db: Session = Depends(get_db)):
  """Exportar datos desde db a csv"""
  return RilesService.export_pdf_data(db)

@router.post("/api/v1/import-pdf-data", status_code=status.HTTP_201_CREATED)
async def import_pdf_data(
  file: UploadFile = File(...), db: Session = Depends(get_db)
):
  """Importar datos desde un archivo CSV a la base de datos a"""
  return await RilesService.import_pdf_data_csv(file, db)

@router.post("/api/v1/update-pdf-data", status_code=status.HTTP_201_CREATED)
async def update_pdf_data_csv(
  file: UploadFile = File(...), db: Session = Depends(get_db)
):
  """Importar y actualizar datos desde un archivo CSV a la base de datos"""
  return await RilesService.update_pdf_data_csv(file, db)

@router.post(
  "/api/v1/replace-pdf-data",
  status_code=status.HTTP_200_OK,
  response_model=List[Dict[str, Any]],
  summary="Reemplazar completamente los datos desde un CSV",
  description="Respalda los datos existentes, trunca la tabla e importa los registros del CSV dentro de una transacción atómica.",
)
async def replace_pdf_data_csv(
  file: UploadFile = File(...), db: Session = Depends(get_db)
):
  """
  Importa y reemplaza la totalidad de los datos desde un archivo CSV.
  Devuelve el conjunto de datos previo antes de la eliminación.
  """
  datos_anteriores = await RilesService.replace_pdf_data_with_backup(
    file=file, db=db
  )
  return datos_anteriores

@router.post("/api/v1/transform-xlsx-to-valid-csv", status_code=status.HTTP_201_CREATED)
async def transform_excel_endpoint(file: UploadFile = File(...), file_name:str="Datos_adaptados"):
  """Recibe un archivo Excel (.xlsx), lo transforma al formato estandarizado y devuelve el archivo CSV descargable."""
  csv_file_bytes = await ExcelTransformService.transform_excel_to_csv_buffer(
      file
  )

  filename = f"{file_name}.csv"

  return StreamingResponse(
      csv_file_bytes,
      media_type='text/csv',
      headers={'Content-Disposition': f'attachment; filename="{filename}"'},
  )

#====================================
# Inbox
#====================================

@router.post("/api/v1/set-inbox-params", status_code=status.HTTP_201_CREATED)
def set_inbox(payload: List[PDFInboxSchema], db: Session = Depends(get_db)):
  return InboxService.set_inbox(payload, db)


@router.patch("/api/v1/deactivate-inbox-file", status_code=status.HTTP_200_OK)
def deactivate_inbox_file(
  payload: List[str] = Body(...), db: Session = Depends(get_db)
):
  return InboxService.deactivate_inbox_file(payload, db)

@router.patch("/api/v1/deactivate-inbox-mail", status_code=status.HTTP_200_OK)
def deactivate_inbox_mail(
  payload: List[str] = Body(...), db: Session = Depends(get_db)
):
  return InboxService.deactivate_inbox_mail(payload, db)



@router.get("/api/v1/get-inbox", status_code=status.HTTP_200_OK)
def get_inbox_params(
  page: int = 1,
  page_size: int = 5,
  db: Session = Depends(get_db)
):
  return InboxService.get_inbox_params(db, page, page_size)


@router.get("/api/v1/get-deactivated-inbox", status_code=status.HTTP_200_OK)
def get_deactivated_inbox_ids(db: Session = Depends(get_db)):
  return InboxService.get_deactivated_inbox_ids(db)


@router.get("/api/v1/get-opened-inbox", status_code=status.HTTP_200_OK)
def get_opened_inbox_ids(db: Session = Depends(get_db)):
  return InboxService.get_opened_inbox_ids(db)


@router.delete("/api/v1/clear-inbox", status_code=status.HTTP_200_OK)
def clear_inbox_table(db: Session = Depends(get_db)):
  return InboxService.clear_inbox_table(db)

#====================================
# Parámetros
#====================================

@router.post(
  "/api/v1/parameter-limits",
  summary="Cargar límites de parámetros desde Excel/CSV",
  status_code=status.HTTP_201_CREATED,
  response_model=List[ParametroResponse],
)
async def set_parameters_limits(
  file: UploadFile = File(...), db: Session = Depends(get_db)
):
  return await ParameterService.set_parameters_limits(file, db)

@router.put(
  "/api/v1/parameter-limits/{param_id}",
  summary="Actualizar un parámetro por ID",
  status_code=status.HTTP_200_OK,
  response_model=ParametroResponse,
)
async def update_parameter_limit(
  param_id: int, param_data: ParametroUpdate, db: Session = Depends(get_db)
):
  return ParameterService.update_parameter_limit(param_id, param_data, db)

@router.get(
  "/api/v1/parameter-limits",
  summary="Obtener todos los parámetros",
  status_code=status.HTTP_200_OK,
  response_model=List[ParametroResponse],
)
async def get_parameters_limits(db: Session = Depends(get_db)):
  return ParameterService.get_parameters_limits(db)

#====================================
# Evaluación
#====================================

@router.get(
  "/api/v1/tolerance",
  summary="Obtener nivel de tolerancia",
  status_code=status.HTTP_200_OK,
)
async def get_analysis_tolerance(
  analysis_id: Optional[int] = None,
  local_id: Optional[int] = None,
  db: Session = Depends(get_db),
):
  return RilesService.get_analysis_tolerance(analysis_id, local_id, db)

@router.delete("/api/v1/delete-param-eval", status_code=status.HTTP_201_CREATED)
async def delete_parameter_evaluation(db: Session = Depends(get_db)):
  return RilesService.delete_parameter_evaluation(db)

@router.post(
  "/api/v1/evaluar-analisis/{id_analisis}", status_code=status.HTTP_201_CREATED
)
async def evaluar_analisis(id_analisis: int, db: Session = Depends(get_db)):
  return RilesService.evaluar_analisis(id_analisis, db)

#====================================
# Mailing
#====================================

@router.get(
  "/api/v1/get-mailing-queue",
  summary="Obtener estado de correo por analisis",
  status_code=status.HTTP_200_OK
)
def get_mailing_queue_by_id(analysis_id: Optional[str] = None,db: Session = Depends(get_db)):
  
  if not analysis_id:
    return RilesService.get_mailing_queue(db)
  else:
    return RilesService.get_mailing_queue_by_id(analysis_id,db)

@router.get(
    "/api/v1/export-mailing-queue_csv",
    summary="Exportar estado de correo por análisis",
    status_code=status.HTTP_200_OK
)
def export_mailing_queue(
    analysis_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if not analysis_id:
        data = RilesService.get_full_mailing_queue(db)
    else:
        data = RilesService.get_mailing_queue_by_id(
            analysis_id,
            db
        )

    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados
    writer.writerow([
        "id_analisis",
        "status_local",
        "status_sanitaria"
    ])

    # Datos
    for item in data:
        writer.writerow([
            item.id,
            item.id_analisis,
            item.status_local,
            item.status_sanitaria
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=mailing_queue.csv"
        }
    )

@router.post(
    "/api/v1/insert-mailing-queue",
    summary="Insertar cola de mailing desde CSV",
    status_code=status.HTTP_201_CREATED
)
async def insert_mailing_queue(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await RilesService.insert_mailing_queue_csv(
        file=file,
        db=db
    )

@router.post(
    "/api/v1/update-mailing-queue",
    summary="Actualizar cola de mailing desde CSV",
    status_code=status.HTTP_200_OK
)
async def update_mailing_queue(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return await RilesService.update_mailing_queue_csv(
        file=file,
        db=db
    )

@router.delete("/api/v1/delete-mailing-queue", status_code=status.HTTP_201_CREATED)
async def delete_mailing_queue(db: Session = Depends(get_db)):
  return RilesService.delete_mailing_queue(db)

@router.post("/api/v1/send-analysis-mailing", status_code=status.HTTP_201_CREATED)
async def send_analysis_mailing(
  analysis_id: int, type:str, db: Session = Depends(get_db)
  
):
  return RilesService.send_analysis_mailing(analysis_id,type, db)

#====================================
# Locales
#====================================

@router.get("/api/v1/get-stores", status_code=status.HTTP_201_CREATED)
async def get_locales(
  db: Session = Depends(get_db)
):
  return await StoreService.get_stores(db)

@router.get("/api/v1/get-locales", status_code=status.HTTP_201_CREATED)
async def get_locales(
  analysis_id: int, db: Session = Depends(get_db)
):
  return RilesService.send_analysis_mailing(analysis_id, db)

@router.post(
    "/api/v1/set-locales",
    summary="Cargar locales desde CSV",
    status_code=status.HTTP_201_CREATED,
    response_model=List[StoreResponse])
async def set_locales(
  file: UploadFile = File(...), db: Session = Depends(get_db)
):
  return await StoreService.set_stores(file, db)

@router.delete(
    "/api/v1/delete-locales",
    summary="Borra todos los locales",
    status_code=status.HTTP_201_CREATED)
async def delete_locales(
  db: Session = Depends(get_db)
):
  return await StoreService.delete_stores(db)

@router.get(
  "/api/v1/download-locales",
  response_class=StreamingResponse,
  status_code=status.HTTP_200_OK,
)
async def download_locales(db: Session = Depends(get_db)):
  return await StoreService.export_stores_csv(db)

@router.get(
  "/api/v1/get-local-ids",
  response_model=List[str],
  status_code=status.HTTP_200_OK,
)
async def get_local_ids(db: Session = Depends(get_db)):
  return await StoreService.get_stores_ids(db)

@router.get(
  "/api/v1/get-local-summarized",
  response_model=List[dict],
  status_code=status.HTTP_200_OK,
)
async def get_local_summarized(db: Session = Depends(get_db)):
  return await StoreService.get_stores_summarized(db)

@router.get(
  "/api/v1/get-local-analysis",
  response_model=List[dict],
  status_code=status.HTTP_200_OK,
)
async def get_local_analysis(db: Session = Depends(get_db)):
  return await StoreService.get_stores_analysis(db)


# ====================================
# Mailing por local
# ====================================

# ------------------------------------
# 1. Rutas Estáticas / Específicas
# ------------------------------------

@router.get(
  "/mail",
  response_model=List[LocalMailSchema],
  summary="Obtener todos los correos",
  status_code=status.HTTP_200_OK
)
def get_all_mails(
  skip: int = Query(0, ge=0, description="Registros a omitir (Paginación)"),
  limit: int = Query(100, ge=1, le=500, description="Límite de registros a retornar"),
  db: Session = Depends(get_db)
):
  """
  Retorna la lista paginada de todos los correos configurados para los locales.
  """
  return LocalMailService.get_all_mails(db=db, skip=skip, limit=limit)


@router.post(
  "/mail",
  response_model=LocalMailSchema,
  summary="Crear un nuevo correo",
  status_code=status.HTTP_201_CREATED
)
def create_mail(
  mail_data: LocalMailBase,
  db: Session = Depends(get_db)
):
  """
  Crea un nuevo registro de correo para un local.
  """
  return LocalMailService.create_mail(db=db, mail_data=mail_data)


@router.post(
  "/mail/bulk-upload",
  summary="Carga masiva desde CSV (Sin borrar existentes)",
  status_code=status.HTTP_201_CREATED
)
def bulk_insert_from_csv(
  file: UploadFile = File(..., description="Archivo CSV con columnas: id_local, mail, mail_type"),
  db: Session = Depends(get_db)
):
  """
  Sube un archivo CSV y añade los correos contenidos en él sin borrar la información actual de la base de datos.
  """
  return LocalMailService.bulk_insert_from_csv(db=db, file=file)


@router.post(
  "/mail/update-all-csv",
  summary="Reemplazo total desde CSV (Borra todo e inserta)",
  status_code=status.HTTP_200_OK
)
def update_all_from_csv(
  file: UploadFile = File(..., description="Archivo CSV con columnas: id_local, mail, mail_type"),
  db: Session = Depends(get_db)
):
  """
  Elimina TODOS los registros actuales de la tabla `local_mail` y la vuelve a poblar con los registros del CSV.
  """
  return LocalMailService.update_all_from_csv(db=db, file=file)


@router.delete(
  "/mail/delete-all",
  summary="Eliminación total de registros",
  status_code=status.HTTP_200_OK
)
def delete_all(
  db: Session = Depends(get_db)
):
  """
  Elimina TODOS los registros actuales de la tabla `local_mail`.
  """
  return LocalMailService.delete_all(db=db)


# ------------------------------------
# 2. Rutas con Prefijos Específicos
# ------------------------------------

@router.get(
  "/mail/local/{id_local}",
  response_model=List[LocalMailSchema],
  summary="Obtener correos por local",
  status_code=status.HTTP_200_OK
)
def get_mails_by_local(
  id_local: str = Path(..., description="Identificador/CECO del local"),
  mail_type: Optional[str] = Query(None, description="Filtro opcional por tipo ('local' o 'sanitaria')"),
  db: Session = Depends(get_db)
):
  """
  Obtiene todos los correos asociados a un local específico. Opcionalmente se puede filtrar por tipo de correo.
  """
  return LocalMailService.get_mails_by_local(
    db=db,
    id_local=id_local,
    mail_type=mail_type
  )

@router.get("/mail/export-csv", status_code=status.HTTP_200_OK)
def export_local_mails_csv(db: Session = Depends(get_db)):
  csv_buffer = LocalMailService.export_to_csv(db)

  return StreamingResponse(
      iter([csv_buffer.getvalue()]),
      media_type="text/csv",
      headers={
          "Content-Disposition": (
              "attachment; filename=local_mails_export.csv"
          )
      },
  )

# ------------------------------------
# 3. Rutas Dinámicas por ID Primario
# ------------------------------------

@router.get(
  "/mail/{id_local_mail}",
  response_model=LocalMailSchema,
  summary="Obtener correo por ID",
  status_code=status.HTTP_200_OK
)
def get_mail_by_id(
  id_local_mail: int = Path(..., description="ID primario del registro de correo", ge=1),
  db: Session = Depends(get_db)
):
  """
  Obtiene la información de un registro de correo específico por su ID.
  """
  return LocalMailService.get_mail_by_id(db=db, id_local_mail=id_local_mail)


@router.put(
  "/mail/{id_local_mail}",
  response_model=LocalMailSchema,
  summary="Actualizar un correo existente",
  status_code=status.HTTP_200_OK
)
def update_mail(
  mail_data: LocalMailBase,
  id_local_mail: int = Path(..., description="ID del registro a actualizar", ge=1),
  db: Session = Depends(get_db)
):
  """
  Actualiza los datos de un registro de correo existente dado su ID.
  """
  return LocalMailService.update_mail(
    db=db,
    id_local_mail=id_local_mail,
    mail_data=mail_data
  )


@router.delete(
  "/mail/{id_local_mail}",
  summary="Eliminar un correo",
  status_code=status.HTTP_200_OK
)
def delete_mail(
  id_local_mail: int = Path(..., description="ID del registro a eliminar", ge=1),
  db: Session = Depends(get_db)
):
  """
  Elimina un registro de correo por su ID primario.
  """
  return LocalMailService.delete_mail(db=db, id_local_mail=id_local_mail)


#====================================
# Páginas
#====================================

@router.get("/")
async def inicio(
  request: Request,
  db: Session = Depends(get_db)

  ):
  datos = await StoreService.get_stores_analysis(db)
  return templates.TemplateResponse(
      request=request,
      name="main.html",
      context={"locales": datos}
  )

@router.get("/upload")
async def upload(request: Request):
  datos = {"titulo": "Panel de Lectura de pdf Riles | Medioambiente"}
  return templates.TemplateResponse(
    request=request, name="uploadFiles.html", context=datos
  )


@router.get("/inbox")
async def inbox(request: Request):
  datos = {"titulo": "Panel de Lectura de pdf Riles | Medioambiente"}
  return templates.TemplateResponse(
    request=request, name="inbox.html", context=datos
  )

@router.get("/parameter-limits")
async def parameter_limits(request: Request):
  datos = {"titulo": "Limites de parámetros para riles | Medioambiente"}
  return templates.TemplateResponse(
    request=request, name="paramlimits.html", context=datos
  )


@router.get("/send-mails")
async def parameter_limits(request: Request, db: Session = Depends(get_db)):
  analisis_sin_enviar = RilesService.get_mailing_queue_full_data(db)

  return templates.TemplateResponse(
      request=request,
      name="sendmails.html",
      context={"analisis_list": analisis_sin_enviar},
  )

@router.get("/historico")
async def parameter_limits(request: Request, local:str,db: Session = Depends(get_db)):
  analisis_por_local = RilesService.get_pdf_data_by_store(db=db, store_id=local)

  return templates.TemplateResponse(
      request=request,
      name="records.html",
      context={"analisis_list": analisis_por_local},
  )

@router.get("/data")
async def inbox(request: Request, db: Session = Depends(get_db)):

  datos = RilesService.get_table_status(db=db)
  
  return templates.TemplateResponse(
    request=request, name="data.html", context=datos
  )