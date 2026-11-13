# services/riles_service.py
import base64
from typing import List, Dict, Any, Optional, Set
from fastapi import HTTPException, Response, status,UploadFile,File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..automatizaciones.Envio_correos import main as MailingService
from fastapi.responses import StreamingResponse
from io import BytesIO, TextIOWrapper,StringIO
import csv
import pandas as pd 
from ..riles_config import FILES_DIR

from .models import (
  AnalisisAguaModel,
  PDFInboxModel,
  ParametroModel,
  MailingStatus,
  MailingModel,
  EvaluacionParametrosModel,
  File_b64_Model,
  calcular_estado_parametro,
  parse_float_val,
  MAPEO_NOMBRES_COLUMNAS,
  LocalMailModel,
  StoreModule,
)
from .schemas import AnalisisAguaSchema, File_b64_Schema,MailingSchema,MailingCreate, MailingUpdate
from .mails_service import LocalMailService

class RilesService:
  @staticmethod
  def save_pdf_b64(payload: File_b64_Schema, db: Session) -> Dict[str, Any]:
    try:
      analisis_existente = (
        db.query(AnalisisAguaModel)
        .filter(AnalisisAguaModel.id == payload.id_analisis)
        .first()
      )

      if not analisis_existente:
        raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"No se encontró el análisis con ID {payload.id_analisis}",
        )

      registro_b64 = (
        db.query(File_b64_Model)
        .filter(File_b64_Model.id_analisis == payload.id_analisis)
        .first()
      )

      if registro_b64:
        registro_b64.b64 = payload.b64
      else:
        registro_b64 = File_b64_Model(
          id_analisis=payload.id_analisis, b64=payload.b64
        )
        db.add(registro_b64)

      db.commit()
      db.refresh(registro_b64)

      return {
        "status": "success",
        "message": "Archivo Base64 guardado correctamente.",
        "id": registro_b64.id,
        "id_analisis": registro_b64.id_analisis,
      }
    except HTTPException:
      raise
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al guardar el archivo Base64: {str(e)}",
      )

  @staticmethod
  def download_pdf_b64(id_analisis: int, db: Session) -> Response:
    try:
      registro_b64 = (
        db.query(File_b64_Model)
        .filter(File_b64_Model.id_analisis == id_analisis)
        .first()
      )

      if not registro_b64 or not registro_b64.b64:
        raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=(
            "No se encontró un archivo PDF para el análisis ID"
            f" {id_analisis}"
          ),
        )

      cadena_b64 = registro_b64.b64
      if "," in cadena_b64:
        cadena_b64 = cadena_b64.split(",")[1]

      pdf_bytes = base64.b64decode(cadena_b64)
      headers = {
        "Content-Disposition": (
          f"attachment; filename=analisis_{id_analisis}.pdf"
        )
      }

      return Response(
        content=pdf_bytes, media_type="application/pdf", headers=headers
      )
    except HTTPException:
      raise
    except Exception as e:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al generar la descarga del archivo: {str(e)}",
      )

  @staticmethod
  def get_pdf_b64(id_analisis: int, db: Session) -> str:
    registro_b64 = (
      db.query(File_b64_Model)
      .filter(File_b64_Model.id_analisis == id_analisis)
      .first()
    )
    if not registro_b64:
      return ""
    return registro_b64.b64

  @staticmethod
  def procesar_evaluacion_analisis(
    analisis: AnalisisAguaModel, reglas_db: List[ParametroModel], db: Session
  ) -> EvaluacionParametrosModel:
    evaluacion_dict = {"id_analisis": analisis.id}

    mapeo_normalizado = {
      k.strip().lower(): v for k, v in MAPEO_NOMBRES_COLUMNAS.items()
    }

    for regla in reglas_db:
      if not regla.parametro:
        continue

      nombre_parametro_db = regla.parametro.strip().lower()
      campo_nombre = mapeo_normalizado.get(nombre_parametro_db)

      if not campo_nombre or not hasattr(analisis, campo_nombre):
        continue

      valor_raw = getattr(analisis, campo_nombre, None)
      valor_num = parse_float_val(valor_raw)

      if valor_num is not None:
        estado = calcular_estado_parametro(valor_num, regla)
        evaluacion_dict[campo_nombre] = estado
      else:
        evaluacion_dict[campo_nombre] = None

    nueva_evaluacion = EvaluacionParametrosModel(**evaluacion_dict)
    db.add(nueva_evaluacion)

    return nueva_evaluacion

  @staticmethod
  def evaluar_analisis(id_analisis: int, db: Session) -> Dict[str, Any]:
    analisis = (
      db.query(AnalisisAguaModel)
      .filter(AnalisisAguaModel.id == id_analisis)
      .first()
    )
    if not analisis:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No se encontró el análisis con ID {id_analisis}",
      )

    evaluacion_existente = (
      db.query(EvaluacionParametrosModel)
      .filter(EvaluacionParametrosModel.id_analisis == id_analisis)
      .first()
    )

    if evaluacion_existente:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Este análisis ya fue evaluado previamente.",
      )

    reglas_db = db.query(ParametroModel).all()
    if not reglas_db:
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No hay parámetros configurados en la tabla parametros.",
      )

    evaluacion_dict = {"id_analisis": id_analisis}
    supera_ratio_global = False

    for regla in reglas_db:
      campo_nombre = MAPEO_NOMBRES_COLUMNAS.get(regla.parametro)
      if not campo_nombre or not hasattr(analisis, campo_nombre):
        continue

      valor_raw = getattr(analisis, campo_nombre, None)
      valor_num = parse_float_val(valor_raw)

      if valor_num is not None:
        estado = calcular_estado_parametro(valor_num, regla)
        evaluacion_dict[campo_nombre] = estado

        if estado == 2:
          supera_ratio_global = True
      else:
        evaluacion_dict[campo_nombre] = None

    if supera_ratio_global:
      nueva_evaluacion = EvaluacionParametrosModel(**evaluacion_dict)
      db.add(nueva_evaluacion)
      db.commit()
      db.refresh(nueva_evaluacion)

      return {
        "status": "created",
        "message": (
          "Se detectaron parámetros que superan el ratio permitido. Registro"
          " guardado."
        ),
        "evaluacion_id": nueva_evaluacion.id,
        "detalle": evaluacion_dict,
      }

    return {
      "status": "ignored",
      "message": (
        "Ningún parámetro superó el ratio de tolerancia. No se creó registro."
      ),
      "detalle": evaluacion_dict,
    }

  @staticmethod
  def get_pdf_data(analysis_id: Optional[int], db: Session) -> List[AnalisisAguaModel]:
    try:
      return (
        db.query(AnalisisAguaModel)
        .filter(AnalisisAguaModel.id == analysis_id)
        .all()
      )
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al consultar los datos de ${analysis_id}: {str(e)}",
      )
    
  @staticmethod
  def get_pdf_data_by_store(store_id: Optional[int], db: Session) -> List[AnalisisAguaModel]:
    try:
      return (
        db.query(AnalisisAguaModel)
        .filter(AnalisisAguaModel.local_id == store_id)
        .all()
      )
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al consultar los datos de ${store_id}: {str(e)}",
      )

  @staticmethod
  def save_pdf_data(
    payload: List[AnalisisAguaSchema], db: Session
  ) -> Dict[str, Any]:
    try:
      reglas_db = db.query(ParametroModel).all()
      if not reglas_db:
        raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="No hay parámetros de norma configurados en la base de datos.",
        )

      registros_procesados = 0

      for item in payload:
        item_dict = item.model_dump()
        item_id = item_dict.pop("id", None)
        contenido_b64 = item_dict.pop("b64", None)
        new_dict = {}

        for key, value in item_dict.items():
          if isinstance(value, str):
            new_dict[key] = value.replace(",", ".")
          else:
            new_dict[key] = value

        # A. Comprobar si el registro ya existe
        analisis_registro = None

        if item_id:
          analisis_registro = (
            db.query(AnalisisAguaModel)
            .filter(AnalisisAguaModel.id == item_id)
            .first()
          )

        if analisis_registro:
          # Actualizar registro existente
          for key, value in new_dict.items():
            if hasattr(analisis_registro, key):
              setattr(analisis_registro, key, value)
        else:
          # Crear nuevo registro
          analisis_registro = AnalisisAguaModel(**new_dict)
          db.add(analisis_registro)

        db.flush()
        db.refresh(analisis_registro)
        new_id = analisis_registro.id
        # B. Manejo del archivo Base64 (evita duplicados)
        if contenido_b64:
          registro_b64 = (
            db.query(File_b64_Model)
            .filter(File_b64_Model.id_analisis == analisis_registro.id)
            .first()
          )
          if registro_b64:
            registro_b64.b64 = contenido_b64
          else:

            db.add(File_b64_Model(id_analisis=analisis_registro.id, b64=contenido_b64))
            print("File create")

            try:
              file = base64.b64decode(contenido_b64)
              file_name = f'{new_id}_{new_dict["fecha_muestreo"].strftime("%Y%m")}_{new_dict["local_id"]}.pdf'
              file_path = FILES_DIR / file_name
              with open(file_path, "wb") as archivo:
                archivo.write(file)

            except Exception as e:
              print(str(e))

        # C. Reevaluación de Parámetros (Limpiar previa si existe)
        db.query(EvaluacionParametrosModel).filter(
          EvaluacionParametrosModel.id_analisis == analisis_registro.id
        ).delete(synchronize_session=False)
        db.flush()

        # D. Prevenir duplicados en MailingModel
        mailing_existente = (
          db.query(MailingModel)
          .filter(MailingModel.id_analisis == analisis_registro.id)
          .first()
        )

        if not mailing_existente:
          nuevo_mailing = MailingModel(id_analisis=analisis_registro.id)
          db.add(nuevo_mailing)

        # E. Procesar evaluación con las reglas
        RilesService.procesar_evaluacion_analisis(
          analisis=analisis_registro, reglas_db=reglas_db, db=db
        )

        registros_procesados += 1

      db.commit()

      return {
        "status": "success",
        "message": f"Se procesaron {registros_procesados} registros correctamente.",
        "count": registros_procesados,
      }
    except HTTPException:
      db.rollback()
      raise

    except Exception as e:
      db.rollback()
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al guardar o actualizar en la base de datos: {str(e)}",
      )
    
  @staticmethod
  def update_pdf_data(
    analysis_id: int, payload: AnalisisAguaSchema, db: Session
  ) -> Dict[str, Any]:
    try:
      registro_existente = (
        db.query(AnalisisAguaModel)
        .filter(AnalisisAguaModel.id == analysis_id)
        .first()
      )

      if not registro_existente:
        raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"No se encontró el análisis con ID {analysis_id}",
        )

      for key, value in payload.model_dump().items():
        if key != "id" and hasattr(registro_existente, key):
          setattr(registro_existente, key, value)

      db.commit()
      db.refresh(registro_existente)

      return {
        "status": "success",
        "message": f"Registro con ID {analysis_id} actualizado correctamente.",
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al actualizar en la base de datos: {str(e)}",
      )

  @staticmethod
  def delete_pdf_data(db: Session) -> Dict[str, Any]:
    try:

      db.query(EvaluacionParametrosModel).delete(synchronize_session=False)


      um_rows_deleted = db.query(AnalisisAguaModel).delete(
        synchronize_session=False
      )
      db.commit()

      return {
        "status": "success",
        "message": (
          f"Se Eliminaron {um_rows_deleted} registros, de la tabla"
          " analisis_agua"
        ),
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al guardar en la base de datos: {str(e)}",
      )

  @staticmethod
  async def replace_pdf_data_with_backup(
    file: UploadFile,
    db: Session
  ):
    datos_anteriores = RilesService.export_pdf_data(db=db)

    RilesService.delete_pdf_data(db=db)

    RilesService.import_pdf_data_csv(
        file=file,
        db=db
    )

    db.commit()

    return datos_anteriores


  @staticmethod
  def get_analysis_tolerance(
    analysis_id: Optional[int], local_id: Optional[int], db: Session
  ) -> List[Dict[str, Any]]:
    query = db.query(AnalisisAguaModel, EvaluacionParametrosModel).join(
      EvaluacionParametrosModel,
      AnalisisAguaModel.id == EvaluacionParametrosModel.id_analisis,
    )

    if analysis_id is not None:
      query = query.filter(AnalisisAguaModel.id == analysis_id)
    elif local_id is not None:
      query = query.filter(AnalisisAguaModel.local_id == local_id)
    else:
      return []

    consulta = query.all()
    resultado_final = []

    columnas_evaluacion = [
      c.key
      for c in EvaluacionParametrosModel.__table__.columns
      if c.key not in ("id", "id_analisis")
    ]

    for analisis, evaluacion in consulta:
      parametros_tolerables = []
      parametros_extremos = []
      parametros_correctos = []

      for parametro in columnas_evaluacion:
        estado = getattr(evaluacion, parametro, None)

        if estado is None:
          continue

        valor_raw = getattr(analisis, parametro, None)
        valor_parsed = parse_float_val(valor_raw)

        detalle_parametro = {
          "parametro": parametro,
          "estado": estado,
          "valor": valor_parsed,
        }

        if estado == 1:
          parametros_tolerables.append(detalle_parametro)
        elif estado == 2:
          parametros_extremos.append(detalle_parametro)
        else:
          parametros_correctos.append(detalle_parametro)

      es_tolerable = len(parametros_extremos) == 0

      resultado_final.append({
        "analysis_id": analisis.id,
        "tolerable": es_tolerable,
        "cant_parametros_tolerables": len(parametros_tolerables),
        "cant_parametros_extremos": len(parametros_extremos),
        "parametros_tolerables": parametros_tolerables,
        "parametros_extremos": parametros_extremos,
        "parametros_correctos": parametros_correctos,
      })

    return resultado_final

  @staticmethod
  def get_mailing_queue(db: Session) -> List[MailingModel]:
    try:
      return (
        db.query(MailingModel)
        .filter(
            (MailingModel.status_local == "PENDIENTE") |
            (MailingModel.status_sanitaria == "PENDIENTE")
        )
        .all()
      )
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al consultar tabla mailing: {str(e)}",
      )

  @staticmethod
  def get_full_mailing_queue(db: Session) -> List[MailingModel]:
      try:
        return (
          db.query(MailingModel)
          .all()
        )
      except Exception as e:
        db.rollback()
        raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al consultar tabla mailing: {str(e)}",
        )
      
  @staticmethod
  def get_mailing_queue_by_id(analysis_id : str,db: Session) -> dict:
      try:
        return (
          db.query(MailingModel)
          .filter(
            MailingModel.status_local == "PENDIENTE" or MailingModel.status_sanitaria == "PENDIENTE",
            MailingModel.id_analisis == analysis_id
            )
          .all()
        )
      except Exception as e:
        db.rollback()
        raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al consultar tabla mailing: {str(e)}",
        )
  @staticmethod
  def _obtener_buffer_y_delimitador(content: bytes) -> tuple[StringIO, str]:
    """Auxiliar privado para decodificar el CSV y detectar el delimitador dinámicamente."""
    try:
      decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
      decoded_content = content.decode("latin-1")

    buffer = StringIO(decoded_content)
    sample_text = buffer.read(2048)
    buffer.seek(0)

    try:
      dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t")
      delimiter = dialect.delimiter
    except Exception:
      delimiter = ";"

    return buffer, delimiter

  @staticmethod
  async def insert_mailing_queue_csv(
    file: UploadFile, db: Session
  ) -> Dict[str, Any]:
    # Leer CSV
    content = await file.read()
    buffer, delimiter = RilesService._obtener_buffer_y_delimitador(content)
    reader = csv.DictReader(buffer, delimiter=delimiter)

    modelos_a_insertar: List[MailingModel] = []

    for row in reader:
      clean_row = {
        k.strip(): v.strip() if v else None for k, v in row.items() if k
      }
      esquema_item = MailingCreate(**clean_row)

      # Unicamente creamos la entidad de la cola de mailing vinculando el FK escalar
      nuevo_mailing = MailingModel(
        id_analisis=esquema_item.id_analisis,
        status_local=getattr(
          esquema_item, "status_local", MailingStatus.PENDIENTE
        ),
        status_sanitaria=getattr(
          esquema_item, "status_sanitaria", MailingStatus.PENDIENTE
        ),
      )
      modelos_a_insertar.append(nuevo_mailing)

    # Inserción aislada solo en la tabla mailing
    db.add_all(modelos_a_insertar)
    db.commit()

    return {
      "status": "success",
      "message": (
        f"Se insertaron {len(modelos_a_insertar)} registros en la cola de"
        " mailing."
      ),
      "count": len(modelos_a_insertar),
    }
  
  @staticmethod
  async def update_mailing_queue_csv(
      file: UploadFile,
      db: Session
  ) -> Dict[str, Any]:
      
      print("========== INICIO ==========")
      print("ARCHIVO:", file.filename)

      content = await file.read()

      print("BYTES:", len(content))
      print("CONTENIDO RAW:")
      print(content[:500])

      buffer, delimiter = RilesService._obtener_buffer_y_delimitador(
          content
      )

      print("DELIMITADOR:", repr(delimiter))
      print("BUFFER:", buffer)

      reader = csv.DictReader(
          buffer,
          delimiter=delimiter
      )

      print("COLUMNAS:", reader.fieldnames)

      filas = list(reader)

      print("CANTIDAD FILAS:", len(filas))
      print("FILAS:", filas)

      for row in filas:

          print("ROW ORIGINAL:", row)

          clean_row = {
              key.strip(): value.strip() if value else None
              for key, value in row.items()
              if key
          }

          print("ROW LIMPIA:", clean_row)

          id_analisis = int(
              clean_row["id_analisis"]
          )

          registro = (
              db.query(MailingModel)
              .filter(
                  MailingModel.id_analisis == id_analisis
              )
              .first()
          )

          print(
              "REGISTRO ENCONTRADO:",
              registro
          )

          if registro is None:
              raise HTTPException(
                  status_code=404,
                  detail=f"No existe id_analisis={id_analisis}"
              )

          registro.status_local = clean_row["status_local"]
          registro.status_sanitaria = clean_row["status_sanitaria"]

          print(
              "NUEVOS VALORES:",
              registro.status_local,
              registro.status_sanitaria
          )

      db.commit()

      print("========== COMMIT OK ==========")

      return {
          "status": "success",
          "message": "Datos actualizados correctamente"
      }

  @staticmethod
  def delete_mailing_queue(db: Session) -> Dict[str, Any]:
    try:
      um_rows_deleted = db.query(MailingModel).delete(
        synchronize_session=False
      )
      db.commit()

      return {
        "status": "success",
        "message": (
          f"Se Eliminaron {um_rows_deleted} registros, de la tabla mailing"
        ),
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al guardar en la base de datos: {str(e)}",
      )

  @staticmethod
  def delete_parameter_evaluation(db: Session) -> Dict[str, Any]:
    try:
      um_rows_deleted = db.query(EvaluacionParametrosModel).delete(
        synchronize_session=False
      )
      db.commit()

      return {
        "status": "success",
        "message": (
          f"Se Eliminaron {um_rows_deleted} registros, de la tabla"
          " evaluacion_parametros"
        ),
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al guardar en la base de datos: {str(e)}",
      )

  @staticmethod
  def get_mails_by_local(
      local_id: str, mail_type: str, db: Session
  ) -> List[str]:
    """Obtiene la lista de correos según el local y el tipo ('local' o 'sanitaria')."""
    records = (
        db.query(LocalMailModel)
        .filter(
            LocalMailModel.id_local == str(local_id),
            LocalMailModel.mail_type == mail_type,
        )
        .all()
    )

    return [r.mail for r in records if r.mail]

  
  @staticmethod
  def send_analysis_mailing(
      analysis_id: int,type:str, db: Session
  ) -> Dict[str, Any]:
    res_tolerance = RilesService.get_analysis_tolerance(
        analysis_id=analysis_id, local_id=None, db=db
    )
    res_pdf_data = RilesService.get_pdf_data(analysis_id=analysis_id, db=db)
    res_download_b64 = RilesService.get_pdf_b64(id_analisis=analysis_id, db=db)
    res_mails = LocalMailService.get_mails_by_local(id_local=res_pdf_data[0].local_id,mail_type=type,db=db)
    recipients = []
    print(res_mails)
    for item in res_mails:
      print(item.mail)
      recipients.append(item.mail)
    
    if not res_tolerance or not res_pdf_data:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail=f"No se encontraron datos para el análisis {analysis_id}",
      )

    first_pdf = res_pdf_data[0]
    pdf_dict = (
        first_pdf.__dict__ if hasattr(first_pdf, "__dict__") else first_pdf
    )
    tolerance_dict = (
        res_tolerance[0] if isinstance(res_tolerance, list) else {}
    )

    data = {**tolerance_dict, **pdf_dict}

    try:
      # 1. Ejecutar el envío del correo
      if len(recipients)==0:
        return {
          "status": "failure",
          "message": f"Correo no enviado",
        }
      
      print(data,recipients)
      MailingService.run(data = data, recipients=recipients,type=type)
      
      # 2. Buscar si ya existe un registro de Mailing para este análisis
      mailing_record = (
          db.query(MailingModel)
          .filter(MailingModel.id_analisis == analysis_id)
          .first()
      )

      if mailing_record:
        # Si ya existe, se actualizan los estados a ENVIADO
        if type == "local":
          mailing_record.status_local = MailingStatus.ENVIADO
        else:
          mailing_record.status_sanitaria = MailingStatus.ENVIADO
      else:
        # Si no existe, se crea una nueva fila con estado ENVIADO
        mailing_record = MailingModel(
            id_analisis=analysis_id,
            status_local=MailingStatus.ENVIADO,
            status_sanitaria=MailingStatus.ENVIADO,
        )
        db.add(mailing_record)

      # 3. Confirmar la transacción en la base de datos
      db.commit()

      return {
          "status": "success",
          "message": f"Correo enviado para el análisis {analysis_id}",
      }

    except SQLAlchemyError as e:
      db.rollback()
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=(
              "Correo enviado pero falló el registro en base de datos:"
              f" {str(e)}"
          ),
      )
    except Exception as e:
      db.rollback()
      # Opcional: Registrar el fallo en la base de datos como MailingStatus.ERROR si se requiere
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al enviar el correo del análisis {analysis_id}: {str(e)}",
      )



  @staticmethod
  def export_pdf_data(db: Session) -> StreamingResponse:
    try:
      registros = db.query(AnalisisAguaModel).all()

      bytes_buffer = BytesIO()
      text_buffer = TextIOWrapper(
        bytes_buffer, encoding="utf-8-sig", newline=""
      )
      writer = csv.writer(text_buffer, delimiter=";")

      # Obtener las columnas dinámicas del modelo excepto las internas/llaves primarias si no se requieren
      columnas_model = [
        c.key
        for c in AnalisisAguaModel.__table__.columns
      ]

      writer.writerow(columnas_model)

      for registro in registros:
        fila = [getattr(registro, col, "") for col in columnas_model]
        writer.writerow(fila)

      text_buffer.flush()
      bytes_buffer.seek(0)

      headers = {
        "Content-Disposition": (
          "attachment; filename=analisis_agua_exportados.csv"
        )
      }

      return StreamingResponse(
        iter([bytes_buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
      )
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al generar la exportación CSV: {str(e)}",
      )

  @staticmethod
  async def import_pdf_data_csv(
    file: UploadFile, db: Session
  ) -> Dict[str, Any]:
    if not file.filename.endswith(".csv"):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo proporcionado debe ser un CSV.",
      )

    content = await file.read()

    # Manejo de codificación para soportar UTF-8 con BOM y archivos creados en Windows/Excel
    try:
      decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
      decoded_content = content.decode("latin-1")

    buffer = StringIO(decoded_content)
    reader = csv.DictReader(buffer, delimiter=";")

    payload: List[AnalisisAguaSchema] = []

    for row in reader:
      # Normalizar claves a mayúsculas para evitar desfases por espacios o minúsculas
      clean_row = {
        key.strip(): value.strip() if value else ""
        for key, value in row.items()
        if key
      }

      try:
        # Pydantic mapea automáticamente los nombres del diccionario hacia AnalisisAguaSchema
        esquema_item = AnalisisAguaSchema(**clean_row)
        payload.append(esquema_item)
      except Exception as validation_error:
        raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail=f"Error de validación en la fila del CSV: {str(validation_error)}",
        )

    if not payload:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo CSV se encuentra vacío.",
      )

    # Reutiliza el pipeline completo de persistencia, mailing y evaluación de reglas
    return RilesService.save_pdf_data(payload=payload, db=db)
  
  @staticmethod
  async def update_pdf_data_csv(
    file: UploadFile, db: Session
  ) -> Dict[str, Any]:
    if not file.filename.endswith(".csv"):
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo proporcionado debe ser un CSV.",
      )

    content = await file.read()

    try:
      decoded_content = content.decode("utf-8-sig")
    except UnicodeDecodeError:
      decoded_content = content.decode("latin-1")

    buffer = StringIO(decoded_content)
    reader = csv.DictReader(buffer, delimiter=";")

    payload_map: Dict[int, AnalisisAguaSchema] = {}

    for row_idx, row in enumerate(reader, start=2):
      clean_row = {
        key.strip(): value.strip() if value else None
        for key, value in row.items()
        if key
      }
      print(row)

      try:
        esquema_item = AnalisisAguaSchema(**clean_row)
        
        # Validar la presencia obligatoria del ID para realizar el UPDATE
        if getattr(esquema_item, "id", None) is None:
          raise ValueError("Falta el campo 'id' necesario para la actualización.")
        
        payload_map[esquema_item.id] = esquema_item
      except Exception as validation_error:
        raise HTTPException(
          status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
          detail=f"Error de validación en la fila {row_idx} del CSV: {str(validation_error)}",
        )

    if not payload_map:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El archivo CSV se encuentra vacío o ningún registro contiene un ID válido.",
      )

    try:
      # Cargar reglas de parámetros si se requiere reevaluar las mediciones actualizadas
      reglas_db = db.query(ParametroModel).all()

      # Obtener todos los registros existentes en una sola consulta
      ids_a_actualizar = list(payload_map.keys())
      registros_existentes = (
        db.query(AnalisisAguaModel)
        .filter(AnalisisAguaModel.id.in_(ids_a_actualizar))
        .all()
      )

      existentes_dict = {reg.id: reg for reg in registros_existentes}

      # Validar si hay IDs del CSV que no existen en la Base de Datos
      ids_encontrados = set(existentes_dict.keys())
      ids_faltantes = set(ids_a_actualizar) - ids_encontrados
      
      if ids_faltantes:
        raise HTTPException(
          status_code=status.HTTP_444_NOT_FOUND if hasattr(status, 'HTTP_444_NOT_FOUND') else status.HTTP_404_NOT_FOUND,
          detail=f"Los siguientes IDs no existen en la base de datos: {sorted(list(ids_faltantes))}",
        )

      registros_actualizados = 0

      for id_analisis, datos_nuevos in payload_map.items():
        registro_db = existentes_dict[id_analisis]
        datos_dict = datos_nuevos.model_dump(exclude_unset=True)

        # Extraer campos que no pertenezcan directamente al modelo de análisis
        contenido_b64 = datos_dict.pop("b64", None)
        datos_dict.pop("id", None)

        # Actualizar campos del modelo SQLAlchemy
        for campo, valor in datos_dict.items():
          if hasattr(registro_db, campo):
            setattr(registro_db, campo, valor)

        # Actualizar el archivo Base64 si viene presente en el CSV
        if contenido_b64:
          registro_b64 = (
            db.query(File_b64_Model)
            .filter(File_b64_Model.id_analisis == id_analisis)
            .first()
          )
          if registro_b64:
            registro_b64.b64 = contenido_b64
          else:
            db.add(File_b64_Model(id_analisis=id_analisis, b64=contenido_b64))

        # Reevaluar reglas de negocio y eliminar evaluaciones obsoletas
        if reglas_db:
          db.query(EvaluacionParametrosModel).filter(
            EvaluacionParametrosModel.id_analisis == id_analisis
          ).delete(synchronize_session=False)
          db.flush()

          RilesService.procesar_evaluacion_analisis(
            analisis=registro_db, reglas_db=reglas_db, db=db
          )

        registros_actualizados += 1

      db.commit()

      return {
        "status": "success",
        "message": f"Se actualizaron {registros_actualizados} registros correctamente.",
        "count": registros_actualizados,
      }

    except HTTPException:
      db.rollback()
      raise
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error durante la actualización desde CSV: {str(e)}",
      )
  
  @staticmethod
  async def get_pdf_data_():
    pass

  @staticmethod
  def get_mailing_queue_full_data(db: Session) -> List[Dict[str, Any]]:
    """Consulta la cola de mailing y realiza el JOIN con Análisis y Evaluaciones

    en una sola consulta SQL para evitar el problema N+1.
    """
    try:
      # Un solo JOIN de MailingModel -> AnalisisAguaModel -> EvaluacionParametrosModel
      results = (
          db.query(MailingModel, AnalisisAguaModel, EvaluacionParametrosModel)
          .join(
              AnalisisAguaModel,
              MailingModel.id_analisis == AnalisisAguaModel.id,
          )
          .outerjoin(
              EvaluacionParametrosModel,
              AnalisisAguaModel.id == EvaluacionParametrosModel.id_analisis,
          )
          .filter(
              (MailingModel.status_local == "PENDIENTE")
              | (MailingModel.status_sanitaria == "PENDIENTE")
          )
          .all()
      )

      columnas_evaluacion = [
          c.key
          for c in EvaluacionParametrosModel.__table__.columns
          if c.key not in ("id", "id_analisis")
      ]

      resultado_final = []

      for mailing, analisis, evaluacion in results:
        tolerables_count = 0
        extremos_count = 0

        if evaluacion:
          for parametro in columnas_evaluacion:
            estado = getattr(evaluacion, parametro, None)
            if estado == 1:
              tolerables_count += 1
            elif estado == 2:
              extremos_count += 1

        # Extraer valores seguros para Enums
        status_local_val = getattr(mailing, "status_local", "Sin estado")
        if hasattr(status_local_val, "value"):
          status_local_val = status_local_val.value

        status_sanitaria_val = getattr(mailing, "status_sanitaria", "Sin estado")
        if hasattr(status_sanitaria_val, "value"):
          status_sanitaria_val = status_sanitaria_val.value

        tipo_monitoreo_val = getattr(analisis, "tipo_monitoreo", "N/A")
        if hasattr(tipo_monitoreo_val, "value"):
          tipo_monitoreo_val = tipo_monitoreo_val.value

        resultado_final.append({
            "id_analisis": analisis.id,
            "id_local": analisis.local_id,
            "nombre_local": analisis.local_nombre,
            "status_local": status_local_val.upper(),
            "status_sanitaria": status_sanitaria_val.upper(),
            "tipo_monitoreo": tipo_monitoreo_val,
            "tolerable": (extremos_count == 0),
            "parametros_tolerables_count": tolerables_count,
            "parametros_extremos_count": extremos_count,
        })

      return resultado_final
  
    except Exception as e:
      db.rollback()
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al consultar la cola de correos: {str(e)}",
      )
  @staticmethod
  def get_table_status(db: Session) -> Dict[str, Any]:
    try:
      analisis_count = db.query(AnalisisAguaModel).count()
      evaluacion_count = db.query(EvaluacionParametrosModel).count()
      mailing_count = db.query(MailingModel).count()
      b64_count = db.query(File_b64_Model).count()
      local_mail_count = db.query(LocalMailModel).count()
      store_count = db.query(StoreModule).count()
      payload = {
          "status": "success",
          "message": "Conteo de registros en las tablas.",
          "counts": {
              "analisis_agua": analisis_count,
              "evaluacion_parametros": evaluacion_count,
              "mailing": mailing_count,
              "local_mail": local_mail_count,
              "file_b64": b64_count,
              "stores":store_count
          },
      }
      print(payload)
      return payload
    except Exception as e:
      db.rollback()
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail=f"Error al obtener el estado de las tablas: {str(e)}",
      )