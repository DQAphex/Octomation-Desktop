import importlib
import inspect
import traceback
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.plugin_dependency_manager import PluginDependencyManager


def _safe_print(*args, **kwargs):
  """Evita que un emoji o acento rompa el arranque en consolas cp1252."""
  try:
    print(*args, **kwargs)
  except UnicodeEncodeError:
    text = " ".join(str(arg) for arg in args)
    print(text.encode("ascii", errors="replace").decode("ascii"), **kwargs)


class PluginManager:
  def __init__(self, app: FastAPI, project_root: Path):
    self.app = app
    self.project_root = project_root
    self.plugins_dir = self.project_root / "plugins"
    self.global_static = self.project_root / "static"
    self.global_templates = self.project_root / "templates"
     
    self.template_dirs: List[Path] = []
    self.loaded_plugins: List[str] = []
    self.loaded_plugins_dirs: List[str] = []
    self.failed_plugins: List[Dict[str, object]] = []
    self.dependency_manager = PluginDependencyManager(
      project_root=self.project_root,
      plugins_dir=self.plugins_dir,
    )

  def get_loaded_routers(self):
    return self.loaded_plugins_dirs

  def get_status(self):
    return {
      "loaded": list(self.loaded_plugins),
      "loaded_routers": list(self.loaded_plugins_dirs),
      "failed": list(self.failed_plugins),
      "dependencies": self.dependency_manager.get_report(),
    }
  
  def discover_and_load(self):
    """
    Punto de entrada principal. Inicia el escaneo recursivo y establece 
    los montajes globales como fallback (evitando shadowing).
    """
    if not self.plugins_dir.exists() or not self.plugins_dir.is_dir():
      raise FileNotFoundError(f"Directorio de plugins no encontrado: {self.plugins_dir}")

    # 0. Revisión de dependencias declaradas/importadas ANTES de importar.
    #    Esto permite que un plugin recién descargado desde GitHub tenga sus
    #    librerías instaladas en el venv antes de intentar cargarlo.
    try:
      self.dependency_manager.preflight(self.plugins_dir)
    except Exception as exc:
      _safe_print(f"[WARN] No se pudo completar la revisión previa de dependencias: {exc}")

    # 1. Escaneo topológico de dominios y submódulos (recursivo)
    self._scan_recursively(self.plugins_dir)

    # 2. Montaje estático global (Resolución de fallback en ASGI)
    if self.global_static.exists() and self.global_static.is_dir():
      self.app.mount(
        "/static",
        StaticFiles(directory=str(self.global_static)),
        name="static_global",
      )

    # 3. Persistir reporte de dependencias para diagnóstico posterior
    self.dependency_manager.print_summary()
    self.dependency_manager.save_report()

  def _scan_recursively(self, current_path: Path):
    """
    Recorre el árbol de directorios ignorando artefactos de Python y sistemas,
    delegando la evaluación de recursos cuando detecta un paquete válido.
    """
    for path in current_path.iterdir():
      if path.is_dir() and not path.name.startswith((".", "_", "__")):
        # Prevenir escaneo en carpetas de datos internas del plugin
        if path.name in ["data", "background_processes", "backgroundProcesses", "fails"]:
          continue

        # Una carpeta con guiones u otros caracteres no puede ser un módulo
        # Python. Se reporta una sola vez y no se sigue escaneando.
        if not path.name.isidentifier():
          self._record_failure(
            plugin_id="_".join(path.relative_to(self.plugins_dir).parts),
            module_path=None,
            exc=ValueError(
              f"Nombre de carpeta no válido para Python: {path.name}"
            ),
            hint=(
              "Renombra la carpeta del plugin a snake_case (sin guiones ni "
              "caracteres especiales) para que pueda importarse."
            ),
            plugin_path=path,
          )
          continue

        self._evaluate_plugin_node(path)
        self._scan_recursively(path)

  def _evaluate_plugin_node(self, plugin_path: Path):
    """
    Evalúa un nodo del directorio. Construye espacios de nombres dinámicos 
    basados en la ruta relativa desde la raíz de plugins.
    """
    # Ej: Posición actual: plugins/medioambiente/riles
    # rel_path = medioambiente/riles
    rel_path = plugin_path.relative_to(self.plugins_dir)
    namespace_parts = rel_path.parts
    
    # Si estamos en la raíz de plugins, no hay espacio de nombres
    if not namespace_parts:
      return

    # Construcción de identificadores dinámicos
    # url_namespace -> medioambiente/riles
    # name_namespace -> medioambiente_riles
    url_namespace = "/".join(namespace_parts)
    name_namespace = "_".join(namespace_parts)

    # Un plugin cuyo nombre no es un identificador Python válido (por ejemplo,
    # una carpeta con guiones) no puede importarse. Se reporta explícitamente
    # en lugar de dejar que desaparezca con un ModuleNotFoundError confuso.
    invalid_parts = [part for part in namespace_parts if not part.isidentifier()]
    if invalid_parts:
      self._record_failure(
        plugin_id=name_namespace,
        module_path=None,
        exc=ValueError(
          f"Nombre de carpeta no válido para Python: {plugin_path.name}"
        ),
        hint=(
          "Renombra la carpeta del plugin a snake_case (sin guiones ni "
          "caracteres especiales) para que pueda importarse."
        ),
        plugin_path=plugin_path,
      )
      return

    # --- 1. Montaje de Estáticos Aislados ---
    plugin_static = plugin_path / "static"
    if plugin_static.exists() and plugin_static.is_dir():
      mount_name = f"static_{name_namespace}"
      url_prefix = f"/static/plugins/{url_namespace}"
      
      self.app.mount(
        url_prefix,
        StaticFiles(directory=str(plugin_static)),
        name=mount_name,
      )

    # --- 2. Recolección de Plantillas ---
    for template_folder in ["pages", "templates"]:
      t_dir = plugin_path / template_folder
      if t_dir.exists() and t_dir.is_dir():
        self.template_dirs.append(t_dir)

    # --- 3. Carga Dinámica de Routers (Convención por Homonimia) ---
    # Busca un archivo .py que coincida con el nombre de la carpeta (ej. riles.py)
    # y opcionalmente chequea un main.py como fallback
    entry_points = [
      plugin_path / f"{plugin_path.name}.py",
      plugin_path / "main.py"
    ]

    for entry_point in entry_points:
      if entry_point.exists() and entry_point.is_file():
        if not entry_point.stem.isidentifier():
          self._record_failure(
            plugin_id=name_namespace,
            module_path=None,
            exc=ValueError(
              f"Nombre de archivo no válido para Python: {entry_point.name}"
            ),
            hint=(
              "Renombra el archivo de entrada del plugin a snake_case "
              "(sin guiones ni caracteres especiales)."
            ),
            plugin_path=plugin_path,
          )
          break

        # Transforma plugins/medioambiente/riles/riles.py -> plugins.medioambiente.riles.riles
        module_path = ".".join(["plugins"] + list(namespace_parts) + [entry_point.stem])
        self._import_routers_from_module(
          module_path,
          name_namespace,
          plugin_path=plugin_path,
          entry_file=entry_point,
        )
        break # Si encuentra el router primario, detiene la búsqueda en esta carpeta

  def _import_routers_from_module(
    self,
    module_path: str,
    plugin_id: str,
    plugin_path: Path | None = None,
    entry_file: Path | None = None,
  ):
    max_attempts = self.dependency_manager.max_import_attempts

    for attempt in range(1, max_attempts + 1):
      try:
        # Garantiza dependencias declaradas e imports directos antes de cargar.
        if plugin_path is not None and attempt == 1:
          self.dependency_manager.ensure_plugin_dependencies(
            plugin_path=plugin_path,
            entry_file=entry_file,
            plugin_name=plugin_id,
          )

        module = importlib.import_module(module_path)
        for attr_name, attr_value in inspect.getmembers(module):
          if isinstance(attr_value, APIRouter):
            if getattr(attr_value, "_registered_in_app", False):
              continue
            self.app.include_router(attr_value)
            setattr(attr_value, "_registered_in_app", True)
            self.loaded_plugins.append(f"[{plugin_id}] Montado: {module_path}:{attr_name}")
            self.loaded_plugins_dirs.append(f"{module_path}:{attr_name}")
        return

      except Exception as exc:
        installed_actions = []
        if plugin_path is not None and attempt < max_attempts:
          installed_actions = self.dependency_manager.resolve_import_failure(
            plugin_path=plugin_path,
            exc=exc,
            plugin_name=plugin_id,
          )

        if installed_actions and attempt < max_attempts:
          _safe_print(
            f"[RETRY] Dependencia(s) instalada(s) para {module_path}. "
            f"Reintentando importación ({attempt + 1}/{max_attempts})..."
          )
          continue

        # No se pudo resolver automáticamente: se reporta con diagnóstico.
        self._record_failure(
          plugin_id=plugin_id,
          module_path=module_path,
          exc=exc,
          hint=None,
          plugin_path=plugin_path,
        )
        return

  def _record_failure(
    self,
    plugin_id: str,
    module_path: str | None,
    exc: BaseException,
    hint: str | None = None,
    plugin_path: Path | None = None,
  ) -> None:
    dependency_info = self.dependency_manager.classify_failure(
      exc, plugin_path or self.plugins_dir
    )
    failure = {
      "plugin": plugin_id,
      "module": module_path,
      "error_type": type(exc).__name__,
      "error": str(exc),
      "kind": dependency_info.kind,
      "missing": dependency_info.missing,
      "hint": hint or dependency_info.hint,
    }
    self.failed_plugins.append(failure)

    _safe_print(f"[ERROR] Error crítico en módulo {module_path or plugin_id}: {exc}")
    if failure["hint"]:
      _safe_print(f"   -> {failure['hint']}")
    # El log completo queda disponible en server_error.log.
    if exc.__traceback__ is not None:
      _safe_print(traceback.format_exc())


  def get_jinja_templates(self) -> Jinja2Templates:
    """
    Retorna la instancia de Jinja2 con resolución de fallback.
    Prioridad 1: Plantillas locales del plugin (/plugins/.../pages/)
    Prioridad 2: Plantillas globales (/templates/)
    """
    all_dirs = []
    
    # Inyección de directorios descubiertos en orden de precedencia
    all_dirs.extend([str(d) for d in self.template_dirs])

    if self.global_templates.exists() and self.global_templates.is_dir():
      all_dirs.append(str(self.global_templates))

    return Jinja2Templates(directory=all_dirs)