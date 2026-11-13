from typing import List, Dict, Any
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from .models import ParametroModel
from .schemas import ParametroCreate, ParametroUpdate
from .pdf_service import PDFService


class ParameterService:
  @staticmethod
  async def set_parameters_limits(
    file: UploadFile, db: Session
  ) -> List[ParametroModel]:
    records = await PDFService.parse_parameters_file(file)
    nuevos_parametros = []

    db.query(ParametroModel).delete()

    for record in records:
      param_data = ParametroCreate(**record)
      db_param = ParametroModel(**param_data.model_dump())
      db.add(db_param)
      nuevos_parametros.append(db_param)

    db.commit()

    for param in nuevos_parametros:
      db.refresh(param)

    return nuevos_parametros

  @staticmethod
  def update_parameter_limit(
    param_id: int, param_data: ParametroUpdate, db: Session
  ) -> ParametroModel:
    db_param = (
      db.query(ParametroModel).filter(ParametroModel.id == param_id).first()
    )

    if not db_param:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"El parámetro con ID {param_id} no existe.",
      )

    update_data = param_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
      setattr(db_param, key, value)

    db.commit()
    db.refresh(db_param)

    return db_param

  @staticmethod
  def get_parameters_limits(db: Session) -> List[ParametroModel]:
    return db.query(ParametroModel).all()