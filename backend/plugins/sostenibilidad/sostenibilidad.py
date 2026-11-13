from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from paths import TEMPLATES_DIR
from .no_desperdicio_alimentos import router as no_desperdicio_alimentos

router = APIRouter(
  prefix="/sostenibilidad",
  tags=["Sostenibilidad"]
)

router.include_router(no_desperdicio_alimentos)

templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/")
async def inicio(request: Request):
  datos = {
    "titulo": "Panel de Lectura de pdf No Desperdicio Alimentos | Sostenibilidad"
  }
  return templates.TemplateResponse(
    request=request, 
    name="areas/sostenibilidad.html", 
    context=datos
  )