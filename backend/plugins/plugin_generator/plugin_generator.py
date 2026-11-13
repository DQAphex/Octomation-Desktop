from fastapi import APIRouter, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pathlib import Path
from plugins.generic.snapshot import mapear_directorio
from .dto.plugin_dto import PluginBaseDTO
# Importar Servicio de Creación de plugins
from .services.plugin_service import PluginService

# Rutas principales del plugin
from .plugin_generator_config import SERVICES_DIR,PAGES_DIR
# Carga de Plantilla general de la página
from paths import TEMPLATES_DIR


# Definimos el router
router = APIRouter(
  prefix="/plugin_generator",
  tags=["Plugin Generator"]
)
templates = Jinja2Templates(directory=[PAGES_DIR, TEMPLATES_DIR])


@router.get("/")
async def plugin_generator_page(request:Request):
  """
    Devuelve la página principal para crear plugins
  """
  plugin_manager = request.app.state.plugin_manager

  plugin_list = plugin_manager.get_loaded_routers()
  
  context_data = {
      "request": request, # Es buena práctica incluir request dentro del contexto
      "loaded_routers": plugin_list 
  }

  return templates.TemplateResponse(
    request=request,
    name="main.html",
    context=context_data
  )

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_plugin(payload: PluginBaseDTO):
  """
  Procesa la creación de un nuevo plugin.
  Validación automática de la carga útil vía Pydantic (PluginBaseDTO) y 
  aprovisionamiento de la estructura de archivos en disco.
  """
  service = PluginService(metadata=payload)

  # 1. Validación de conflicto previa a la escritura en el sistema de archivos
  if service.validate_plugin_exists():
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail={
        "code": "PLUGIN_ALREADY_EXISTS",
        "message": f"El plugin '{payload.plugin_name}' ya existe en el directorio especificado.",
        "path": str(service.plugin_path
        )
      }
    )

  # 2. Orquestación y construcción del directorio/archivos en hilo secundario (no bloqueante)
  try:
    created_path: Path = await service.build_plugin_structure_async()

  except Exception as err:
    import traceback

    traceback.print_exc()

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": "PLUGIN_CREATION_FAILED",
            "message": "Ocurrió un error inesperado al generar la estructura del plugin.",
            "details": str(err)
        }
    )

  # except FileNotFoundError as fnf_err:
  #   raise HTTPException(
  #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
  #     detail={
  #       "code": "TEMPLATE_NOT_FOUND",
  #       "message": "Error interno: Faltan archivos de plantilla para la generación del plugin.",
  #       "details": str(fnf_err)
  #     }
  #   )
  # except PermissionError as perm_err:
  #   raise HTTPException(
  #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
  #     detail={
  #       "code": "FS_PERMISSION_DENIED",
  #       "message": "Permisos insuficientes en el sistema de archivos para escribir la carpeta.",
  #       "details": str(perm_err)
  #     }
  #   )
  # except Exception as err:
  #   raise HTTPException(
  #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
  #     detail={
  #       "code": "PLUGIN_CREATION_FAILED",
  #       "message": "Ocurrió un error inesperado al generar la estructura del plugin.",
  #       "details": str(err)
  #     }
  #   )

  # # 3. Respuesta estándar de éxito con metadatos del plugin creado
  # return JSONResponse(
  #   status_code=status.HTTP_201_CREATED,
  #   content={
  #     "status": "success",
  #     "message": "Plugin y estructura de archivos creados exitosamente.",
  #     "data": {
  #       "plugin_path": str(created_path),
  #       "metadata": jsonable_encoder(payload)
  #     }
  #   }
  # )