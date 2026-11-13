# services/inbox_service.py
from typing import List, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import PDFInboxModel
from .schemas import PDFInboxSchema


class InboxService:
  @staticmethod
  def set_inbox(payload: List[PDFInboxSchema], db: Session) -> Dict[str, Any]:
    try:
      nuevos_registros = [
        PDFInboxModel(**item.model_dump()) for item in payload
      ]

      db.add_all(nuevos_registros)
      db.commit()

      cantidad = len(nuevos_registros)

      return {
        "status": "success",
        "message": f"Se guardaron {cantidad} registros correctamente.",
        "count": cantidad,
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al guardar en la base de datos: {str(e)}",
      )

  @staticmethod
  def deactivate_inbox_file(payload: List[str], db: Session) -> Dict[str, Any]:
    if not payload:
      return {
        "status": "success",
        "message": "No se enviaron IDs para inactivar.",
        "count": 0,
      }

    try:
      updated_rows = (
        db.query(PDFInboxModel)
        .filter(PDFInboxModel.id_file.in_(payload))
        .update({PDFInboxModel.is_active: False}, synchronize_session=False)
      )

      db.commit()

      return {
        "status": "success",
        "message": (
          f"Se marcaron {updated_rows} registros como inactivos correctamente."
        ),
        "count": updated_rows,
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al inactivar los registros: {str(e)}",
      )

  @staticmethod
  def deactivate_inbox_mail(payload: List[str], db: Session) -> Dict[str, Any]:
    if not payload:
      return {
        "status": "success",
        "message": "No se enviaron IDs para inactivar.",
        "count": 0,
      }

    try:
      updated_rows = (
        db.query(PDFInboxModel)
        .filter(PDFInboxModel.id_correo.in_(payload))
        .update({PDFInboxModel.is_active: False}, synchronize_session=False)
      )

      db.commit()

      return {
        "status": "success",
        "message": (
          f"Se marcaron {updated_rows} registros como inactivos correctamente."
        ),
        "count": updated_rows,
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al inactivar los registros: {str(e)}",
      )

  @staticmethod
  def get_inbox_params(
    db: Session,
    page: int,
    page_size: int
  ):
    try:
      query = (
        db.query(PDFInboxModel)
        .filter(PDFInboxModel.is_active == True)
      )

      total = query.count()

      offset = (page - 1) * page_size

      items = (
        query
        .offset(offset)
        .limit(page_size)
        .all()
      )

      return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total
      }

    except Exception as e:
      raise HTTPException(
        status_code=500,
        detail=str(e)
      )

  @staticmethod
  def get_deactivated_inbox_ids(db: Session) -> List[str]:
    try:
      items = (
        db.query(PDFInboxModel.id_correo)
        .filter(PDFInboxModel.is_active == False)
        .all()
      )
      return [row[0] for row in items]
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @staticmethod
  def get_opened_inbox_ids(db: Session) -> List[str]:
    try:
      items = db.query(PDFInboxModel.id_correo).all()
      return [row[0] for row in items]
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

  @staticmethod
  def clear_inbox_table(db: Session) -> Dict[str, Any]:
    try:
      num_rows_deleted = db.query(PDFInboxModel).delete(
        synchronize_session=False
      )
      db.commit()

      return {
        "status": "success",
        "message": f"Se eliminaron {num_rows_deleted} registros de la tabla.",
        "count": num_rows_deleted,
      }
    except Exception as e:
      db.rollback()
      raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error al vaciar la tabla: {str(e)}",
      )