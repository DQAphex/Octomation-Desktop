from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
import markdown
import os
from plugins.generic.snapshot import mapear_directorio
from paths import ROOT_DIR, TEMPLATES_DIR

# Definimos el router
router = APIRouter(
  prefix="/documentacion",
  tags=["Documentación"]
)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/api/ejecutar-snapshot")
def ejecutar_snapshot():
  """Endpoint que dispara la automatización de mapeo de archivos."""
  archivo_salida = ROOT_DIR / "mapa_archivos.txt"
  
  # Llamamos a tu función de automatización
  resultado = mapear_directorio(ROOT_DIR, archivo_salida)
  
  return {
    "status": "completado",
    "archivo_generado": str(archivo_salida),
    "structure": resultado
  }

@router.get("/page")
def get_docs_page(request: Request):
  """Página principal de documentación con el menú lateral jerárquico."""
  docs_dir = ROOT_DIR / "docs"
  
  # Estructura: {"NombreCarpeta": [{"nombre": "archivo", "path": "ruta/archivo.md"}]}
  categorias = {}
  
  if docs_dir.exists():
    for raiz, _, archivos in os.walk(docs_dir):
      for archivo in archivos:
        if archivo.endswith(".md"):
          ruta_completa = os.path.join(raiz, archivo)
          ruta_relativa = os.path.relpath(ruta_completa, docs_dir)
          
          # Separar la ruta por carpetas usando el separador del sistema operativo
          partes = ruta_relativa.split(os.sep)
          
          if len(partes) > 1:
            categoria = partes[0]  # Es una subcarpeta
          else:
            categoria = "General"  # Archivos sueltos en la raíz de docs/
            
          if categoria not in categorias:
            categorias[categoria] = []
            
          # Quitamos la extensión .md para mostrar el nombre limpio
          nombre_sin_ext = os.path.splitext(archivo)[0]
          
          categorias[categoria].append({
            "nombre": nombre_sin_ext,
            "path": ruta_relativa.replace("\\", "/")
          })

  return templates.TemplateResponse(
    request,
    name="documentation.html",
    context={"categorias": categorias}
  )

@router.get("/content/{file_path:path}")
def get_md_content(file_path: str):
  """Lee un archivo .md específico, lo convierte a HTML y lo retorna."""
  archivo_objetivo = ROOT_DIR / "docs" / file_path
  
  # Seguridad básica para evitar path traversal
  if not archivo_objetivo.resolve().is_relative_to((ROOT_DIR / "docs").resolve()):
    raise HTTPException(status_code=403, detail="Acceso denegado")
    
  if not archivo_objetivo.exists() or not archivo_objetivo.suffix == ".md":
    raise HTTPException(status_code=404, detail="Documento no encontrado")
    
  with open(archivo_objetivo, "r", encoding="utf-8") as f:
    contenido_md = f.read()
    
  # Configurar las extensiones de Markdown para soportar Mermaid
  extensiones = [
    'tables',
    'codehilite',
    'pymdownx.superfences'
  ]
  
  extension_configs = {
    'pymdownx.superfences': {
      'custom_fences': [
        {
          'name': 'mermaid',
          'class': 'mermaid',
          'format': lambda source, language, css_class, options, md, **kwargs: f'<div class="{css_class}">{source}</div>'
        }
      ]
    }
  }

  # Convertir Markdown a HTML
  contenido_html = markdown.markdown(
    contenido_md, 
    extensions=extensiones,
    extension_configs=extension_configs
  )
  
  return {"html": contenido_html}

@router.get("/page/structure")
def get_proyect_structure(request: Request):
  result = ejecutar_snapshot()

  return templates.TemplateResponse(
    request,
    name="structure.html", 
    context={"result": result}
  )