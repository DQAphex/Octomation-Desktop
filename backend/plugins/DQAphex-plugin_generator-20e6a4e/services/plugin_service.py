import asyncio
import datetime
from pathlib import Path
from typing import List, Optional

from paths import PLUGINS_DIR
from ..dto.plugin_dto import PluginBaseDTO


class PluginService:

  def __init__(self, metadata: PluginBaseDTO) -> None:
    self.plugin_dir: Path = Path(PLUGINS_DIR).resolve()
    self.metadata: PluginBaseDTO = metadata
    self.templates_dir: Path = (Path(__file__).parent / "templates").resolve()

    print("=" * 60)
    print("PLUGIN DIR:", self.plugin_dir)
    print("TEMPLATES DIR:", self.templates_dir)
    print("TEMPLATES EXISTS:", self.templates_dir.exists())
    print("=" * 60)
  # ---------------------------------------------------------------------------
  # Propiedades de Normalización de Nombres y Rutas
  # ---------------------------------------------------------------------------

  @property
  def raw_category(self) -> str:
    """Soporta tanto 'plugin_category' como 'category' en el DTO."""
    cat = getattr(self.metadata, "plugin_category", None) or getattr(self.metadata, "category", None)
    return cat.strip() if cat else ""

  @property
  def category_clean(self) -> str:
    """Formatea la categoría a snake_case."""
    return self.raw_category.lower().replace(" ", "_").replace("-", "_")

  @property
  def plugin_name_clean(self) -> str:
    """Formatea el nombre del plugin a snake_case."""
    return self.metadata.plugin_name.strip().lower().replace(" ", "_").replace("-", "_")

  @property
  def category_path(self) -> Optional[Path]:
    """Retorna la ruta física de la categoría si está configurada."""
    if self.category_clean:
      return self.plugin_dir / self.category_clean
    return None

  @property
  def plugin_path(self) -> Path:
    """Resuelve la ruta final del plugin en el árbol de directorios."""
    if self.category_path:
      return self.category_path / self.plugin_name_clean
    return self.plugin_dir / self.plugin_name_clean

  # ---------------------------------------------------------------------------
  # Validaciones
  # ---------------------------------------------------------------------------

  def validate_category(self) -> bool:
    if self.category_path is None:
      return True
    return self.category_path.is_dir()

  def validate_plugin_exists(self) -> bool:
    return self.plugin_path.is_dir()

  # ---------------------------------------------------------------------------
  # Creación de Directorios
  # ---------------------------------------------------------------------------

  def create_category_folder(self) -> Optional[Path]:
    if self.category_path:
      self.category_path.mkdir(parents=True, exist_ok=True)
      return self.category_path
    return None

  def create_plugin_folder(self) -> Path:
    self.plugin_path.mkdir(parents=True, exist_ok=True)
    return self.plugin_path

  def create_root_folder(self) -> Path:
    self.plugin_path.mkdir(parents=True, exist_ok=True)
    return self.plugin_path

  def create_data_folder(self) -> Path:
    folder = self.plugin_path / "data"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  def create_pages_folder(self) -> Path:
    folder = self.plugin_path / "pages"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  def create_services_folder(self) -> Path:
    folder = self.plugin_path / "services"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  def create_static_folder(self) -> Path:
    folder = self.plugin_path / "static"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  def create_background_processes_folder(self) -> Path:
    folder = self.plugin_path / "backgroundProcesses"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  def create_dto_folder(self) -> Path:
    folder = self.plugin_path / "dto"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

  # ---------------------------------------------------------------------------
  # Creación de Archivos Basados en Plantillas
  # ---------------------------------------------------------------------------

  def _read_template(self, template_name: str) -> str:
    template_file = self.templates_dir / template_name

    print("BUSCANDO TEMPLATE:", template_file)
    print("EXISTE:", template_file.exists())

    if not template_file.exists() or not template_file.is_file():
        raise FileNotFoundError(
            f"La plantilla especificada no fue encontrada: {template_file}"
        )

    return template_file.read_text(encoding="utf-8")

  def create_metadata_json(self) -> Path:

    target_file = self.plugin_path / "metadata.json"
    template_file = self.templates_dir / "metadata.json.template"

    if template_file.exists():
        content = template_file.read_text(encoding="utf-8")

        created_at_val = (
            self.metadata.created_at.isoformat()
            if isinstance(self.metadata.created_at, datetime.datetime)
            else str(self.metadata.created_at)
        )

        try:
          rendered_content = content.format(
            plugin_name=self.metadata.plugin_name,
            plugin_category=self.raw_category,
            version=self.metadata.version,
            author=self.metadata.author,
            email=self.metadata.email,
            created_at=created_at_val
          )

        except Exception as e:
          print("=" * 70)
          print("❌ ERROR AL HACER FORMAT")
          print("TIPO:", type(e).__name__)
          print("MENSAJE:", repr(e))
          print("TEMPLATE RAW:")
          print(repr(content))
          print("=" * 70)
          raise

        print("    [7.8] Template renderizado")

    else:
        print("    [7.5] Template NO existe")
        print("    [7.6] Intentando model_dump_json()")

        rendered_content = self.metadata.model_dump_json(indent=2)

        print("    [7.7] model_dump_json OK")

    print("    [7.9] Escribiendo metadata.json")

    target_file.write_text(
        rendered_content,
        encoding="utf-8"
    )

    print("    [7.10] metadata.json creado")

    return target_file

  def create_init_file(self) -> Path:
    plugin_name_lower = self.plugin_name_clean
    plugin_name_pascal = "".join(
        word.capitalize()
        for word in plugin_name_lower.split("_")
    )

    target_file = self.plugin_path / "__init__.py"

    content = self._read_template("__init__.py.template")

    rendered_content = content.format(
        plugin_name_lower=plugin_name_lower,
        plugin_name_pascal=plugin_name_pascal
    )

    target_file.write_text(
        rendered_content,
        encoding="utf-8"
    )

    return target_file

  def create_main_python_file(self) -> Path:
    raw_name = self.metadata.plugin_name.strip()
    plugin_name_lower = self.plugin_name_clean
    plugin_name_pascal = "".join(word.capitalize() for word in plugin_name_lower.split("_"))
    plugin_name_title = raw_name.replace("_", " ").replace("-", " ").title()

    filename = f"{plugin_name_lower}.py"
    target_file = self.plugin_path / filename
    content = self._read_template("plugin_main.py.template")

    rendered_content = content.format(
      plugin_name_lower=plugin_name_lower,
      plugin_name_pascal=plugin_name_pascal,
      plugin_name_title=plugin_name_title,
      version=self.metadata.version,
      author=self.metadata.author
    )

    target_file.write_text(rendered_content, encoding="utf-8")
    return target_file

  def create_config_python_file(self) -> Path:
    raw_name = self.metadata.plugin_name.strip()
    plugin_name_lower = self.plugin_name_clean

    filename = f"{plugin_name_lower}_config.py"
    target_file = self.plugin_path / filename
    content = self._read_template("plugin_config.py.template")

    rendered_content = content.format(
      plugin_name=raw_name,
      version=self.metadata.version
    )
    target_file.write_text(rendered_content, encoding="utf-8")
    return target_file

  def create_pages_html_file(self) -> Path:
    raw_name = self.metadata.plugin_name.strip()
    plugin_name_lower = self.plugin_name_clean
    plugin_name_title = raw_name.replace("_", " ").replace("-", " ").title()

    category_lower = self.category_clean

    if category_lower:
      name_namespace = f"{category_lower}_{plugin_name_lower}"
      route_prefix = f"/{category_lower}/{plugin_name_lower}"
    else:
      name_namespace = plugin_name_lower
      route_prefix = f"/{plugin_name_lower}"

    static_mount = f"static_{name_namespace}"

    pages_dir = self.plugin_path / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    target_file = pages_dir / "main.html"
    content = self._read_template("main.html.template")

    rendered_content = (
      content.replace("__PLUGIN_NAME_LOWER__", plugin_name_lower)
      .replace("__PLUGIN_TITLE__", plugin_name_title)
      .replace("__ROUTE_PREFIX__", route_prefix)
      .replace("__STATIC_MOUNT__", static_mount)
    )

    target_file.write_text(rendered_content, encoding="utf-8")
    return target_file

  def create_static_css_file(self) -> Path:
    plugin_name_lower = self.plugin_name_clean

    styles_dir = self.plugin_path / "static" / "styles"
    styles_dir.mkdir(parents=True, exist_ok=True)

    target_file = styles_dir / "main.css"
    content = self._read_template("main.css.template")

    rendered_content = content.replace("__PLUGIN_NAME_LOWER__", plugin_name_lower)

    target_file.write_text(rendered_content, encoding="utf-8")
    return target_file

  def create_dto_python_file(self) -> Path:
    plugin_name_lower = self.plugin_name_clean
    plugin_name_pascal = "".join(
        word.capitalize()
        for word in plugin_name_lower.split("_")
    )

    dto_dir = self.plugin_path / "dto"
    dto_dir.mkdir(parents=True, exist_ok=True)

    target_file = dto_dir / f"{plugin_name_lower}_dto.py"

    content = self._read_template("plugin_dto.py.template")

    rendered_content = content.format(
        plugin_name_lower=plugin_name_lower,
        plugin_name_pascal=plugin_name_pascal
    )

    target_file.write_text(
        rendered_content,
        encoding="utf-8"
    )

    return target_file

  def create_category_files(self) -> List[Path]:
    category_lower = self.category_clean
    if not category_lower:
      return []

    category_title = self.raw_category.replace("_", " ").replace("-", " ").title()
    plugin_name_lower = self.plugin_name_clean
    plugin_title = self.metadata.plugin_name.strip().replace("_", " ").replace("-", " ").title()

    category_dir = self.plugin_dir / category_lower
    category_dir.mkdir(parents=True, exist_ok=True)

    generated_files: List[Path] = []

    # 1. Archivo __init__.py de categoría
    init_file = category_dir / "__init__.py"
    if not init_file.exists():
      init_content = f"from .{category_lower} import router\n"
      init_file.write_text(init_content, encoding="utf-8")
      generated_files.append(init_file)

    # 2. Router principal de la categoría
    category_file = category_dir / f"{category_lower}.py"

    if not category_file.exists():
      template_content = self._read_template("category_router.py.template")
      rendered_content = (
        template_content.replace("__CATEGORY_LOWER__", category_lower)
        .replace("__CATEGORY_TITLE__", category_title)
        .replace("__PLUGIN_NAME_LOWER__", plugin_name_lower)
        .replace("__PLUGIN_TITLE__", plugin_title)
      )
      category_file.write_text(rendered_content, encoding="utf-8")
    else:
      content = category_file.read_text(encoding="utf-8")
      import_line = f"from .{plugin_name_lower} import router as {plugin_name_lower}"
      include_line = f"router.include_router({plugin_name_lower})"

      modified = False
      if import_line not in content:
        content = f"{import_line}\n" + content
        modified = True

      if include_line not in content:
        content += f"\n{include_line}\n"
        modified = True

      if modified:
        category_file.write_text(content, encoding="utf-8")

    generated_files.append(category_file)
    return generated_files

  def create_dto_python_file(self) -> Path:
    print("    [3.1] Preparando nombres")

    plugin_name_lower = self.plugin_name_clean

    plugin_name_pascal = "".join(
        word.capitalize()
        for word in plugin_name_lower.split("_")
    )

    print(f"    plugin_name_lower: {plugin_name_lower}")
    print(f"    plugin_name_pascal: {plugin_name_pascal}")

    dto_dir = self.plugin_path / "dto"
    dto_dir.mkdir(parents=True, exist_ok=True)

    print(f"    [3.2] DTO directory: {dto_dir}")

    target_file = dto_dir / f"{plugin_name_lower}_dto.py"

    print(f"    [3.3] Target: {target_file}")

    content = self._read_template("plugin_dto.py.template")

    print("    [3.4] Template leído")
    print(repr(content))

    rendered_content = content.format(
        plugin_name_lower=plugin_name_lower,
        plugin_name_pascal=plugin_name_pascal
    )

    print("    [3.5] Template renderizado")

    target_file.write_text(
        rendered_content,
        encoding="utf-8"
    )

    print("    [3.6] DTO creado")

    return target_file

  def create_service_python_file(self) -> Path:
    plugin_name_lower = self.plugin_name_clean

    plugin_name_pascal = "".join(
        word.capitalize()
        for word in plugin_name_lower.split("_")
    )

    services_dir = self.plugin_path / "services"
    services_dir.mkdir(parents=True, exist_ok=True)

    target_file = services_dir / f"{plugin_name_lower}_service.py"

    content = self._read_template("plugin_service.py.template")

    rendered_content = content.format(
        plugin_name_lower=plugin_name_lower,
        plugin_name_pascal=plugin_name_pascal
    )

    target_file.write_text(
        rendered_content,
        encoding="utf-8"
    )

    return target_file

  # ---------------------------------------------------------------------------
  # Orquestador Principal
  # ---------------------------------------------------------------------------

  def build_plugin_structure(self) -> Path:
    # -----------------------------------------------------------------------
    # 1. Directorio raíz del plugin
    # -----------------------------------------------------------------------
    self.create_root_folder()

    # -----------------------------------------------------------------------
    # 2. Estructura de directorios
    # -----------------------------------------------------------------------
    self.create_data_folder()
    self.create_dto_folder()
    self.create_pages_folder()
    self.create_services_folder()
    self.create_static_folder()
    self.create_background_processes_folder()

    # -----------------------------------------------------------------------
    # 3. Metadata
    # -----------------------------------------------------------------------
    print("[1] Metadata")
    self.create_metadata_json()

    # -----------------------------------------------------------------------
    # 4. Código base del plugin
    # -----------------------------------------------------------------------
    print("[2] create_dto_python_file")

    self.create_dto_python_file()
    print("[3] create_service_python_file")
    self.create_service_python_file()
    print("[4] create_init_file")
    self.create_init_file()
    print("[5] create_main_python_file")
    self.create_main_python_file()
    print("[6] create_config_python_file")
    self.create_config_python_file()

    # -----------------------------------------------------------------------
    # 5. Frontend
    # -----------------------------------------------------------------------
    print("[7] create_pages_html_file")
    self.create_pages_html_file()
    print("[8] create_static_css_file")
    self.create_static_css_file()

    # -----------------------------------------------------------------------
    # 6. Router agregador de categoría
    # -----------------------------------------------------------------------
    print("[9] create_category_files")
    self.create_category_files()

    print("[10] create_category_files")
    
    return self.plugin_path

  # ---------------------------------------------------------------------------
  # Wrappers Asíncronos
  # ---------------------------------------------------------------------------

  async def create_plugin_folder_async(self) -> Path:
    return await asyncio.to_thread(self.create_plugin_folder)

  async def validate_category_async(self) -> bool:
    return await asyncio.to_thread(self.validate_category)

  async def build_plugin_structure_async(self) -> Path:
    return await asyncio.to_thread(self.build_plugin_structure)