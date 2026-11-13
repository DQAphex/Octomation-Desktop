import base64
from fastapi import APIRouter, File, UploadFile, HTTPException, status,Request
from fastapi.staticfiles import StaticFiles
from typing import List


# Parte visual
from paths import Path,TEMPLATES_DIR, STATIC_DIR
from fastapi.templating import Jinja2Templates

from .riles import router as riles
# Incluir módulos de endpoints al backend


# Definimos el router

router = APIRouter(
  prefix="/medioambiente",
  tags=["Medio Ambiente"]
)

router.include_router(riles)

## Extraer los rescursos estáticos y plantillas usando paths.py
templates = Jinja2Templates(directory=TEMPLATES_DIR)


#Endpoints

@router.get("/")
async def inicio(request: Request):
  datos = {"titulo": "Panel de Lectura de pdf Riles | Medioambiente"}
  return templates.TemplateResponse(
      request=request, name="areas/medioambiente.html", context=datos
  )
  

