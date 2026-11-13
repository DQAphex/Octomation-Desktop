from pathlib import Path
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from .dto.no_desperdicio_alimentos_dto import NoDesperdicioAlimentosBaseDTO
from .services.no_desperdicio_alimentos_service import NoDesperdicioAlimentosService
from .no_desperdicio_alimentos_config import PAGES_DIR, SERVICES_DIR
from paths import STATIC_DIR, TEMPLATES_DIR

# Definimos el router
router = APIRouter(
    prefix="/no_desperdicio_alimentos",
    tags=["No Desperdicio Alimentos"]
)

templates = Jinja2Templates(directory=[PAGES_DIR, TEMPLATES_DIR])

@router.get("/")
async def no_desperdicio_alimentos_page(request: Request):
    """
    Devuelve la página principal para el plugin No Desperdicio Alimentos.
    """
    return templates.TemplateResponse(
        request=request,
        name="main.html"
    )


@router.get("/hello-world")
async def hello_world():
    result = NoDesperdicioAlimentosService.get_hola_mundo()

    return {
        "message": result
    }


@router.post("/hello-name")
async def hello_name(data: NoDesperdicioAlimentosBaseDTO):
    result = NoDesperdicioAlimentosService.post_hola_nombre(data)

    return {
        "message": result
    }