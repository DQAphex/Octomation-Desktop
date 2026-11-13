"""
Gestión automática de dependencias de plugins.

El objetivo de este módulo es que un plugin instalado desde GitHub pueda traer
sus propias dependencias y que la aplicación las resuelva al arrancar FastAPI,
sin que el plugin "desaparezca" silenciosamente del listado de routers.

Estrategia (en este orden):

1. Dependencias declaradas por el plugin:
   - requirements.txt / requirements-*.txt
   - pyproject.toml ([project].dependencies y [tool.poetry.dependencies])
   - setup.cfg ([options].install_requires)
   - metadata.json / plugin.json / dependencies.json

2. Dependencias inferidas desde el grafo real de imports del punto de entrada
   del plugin (no se escanea todo el árbol, para no instalar dependencias de
   prototipos o tests que el plugin nunca importa).

3. Dependencias descubiertas en tiempo de importación:
   - ModuleNotFoundError
   - ImportError con mensajes del tipo "X is not installed, run pip install ..."
   - Casos conocidos como EmailStr de Pydantic -> email-validator

Cada paquete faltante se instala con el Python del entorno virtual que ejecuta
la aplicación (`python -m pip install ...`) y luego se reintenta el import.

Variables de entorno opcionales:

- OCTOMATION_AUTO_INSTALL_DEPS=0        Desactiva toda instalación automática.
- OCTOMATION_AUTO_INSTALL_UNKNOWN=0     Solo instala paquetes mapeados/declarados,
                                        no intenta adivinar el nombre PyPI de un
                                        import desconocido.
- OCTOMATION_VENV_PYTHON=<ruta>         Fuerza el intérprete usado para pip.
- OCTOMATION_DEP_INSTALL_TIMEOUT=300    Timeout de cada pip install (segundos).
- OCTOMATION_DEP_PREFLIGHT=0            No revisar dependencias antes de cargar.
- OCTOMATION_PIP_INDEX_URL=<url>        Índice alternativo para pip.
"""

from __future__ import annotations

import ast
import configparser
import importlib
import importlib.metadata as importlib_metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
import time
import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, Optional

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion

try:
    from paths import EXECUTION_DIR
except Exception:  # pragma: no cover - solo como respaldo defensivo
    EXECUTION_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DEFAULT_INSTALL_TIMEOUT = 300
DEFAULT_MAX_IMPORT_ATTEMPTS = 6

ENV_AUTO_INSTALL = "OCTOMATION_AUTO_INSTALL_DEPS"
ENV_AUTO_INSTALL_UNKNOWN = "OCTOMATION_AUTO_INSTALL_UNKNOWN"
ENV_VENV_PYTHON = "OCTOMATION_VENV_PYTHON"
ENV_INSTALL_TIMEOUT = "OCTOMATION_DEP_INSTALL_TIMEOUT"
ENV_PREFLIGHT = "OCTOMATION_DEP_PREFLIGHT"
ENV_PIP_INDEX_URL = "OCTOMATION_PIP_INDEX_URL"

# Carpetas que nunca forman parte del código ejecutable de un plugin.
IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

# Nombres de import que no coinciden con el nombre del paquete en PyPI.
IMPORT_TO_DISTRIBUTION = {
    "attr": "attrs",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "crypto": "pycryptodome",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "email_validator": "email-validator",
    "fitz": "PyMuPDF",
    "gi": "PyGObject",
    "google": "google-api-python-client",
    "jwt": "PyJWT",
    "magic": "python-magic",
    "multipart": "python-multipart",
    "mysql": "mysql-connector-python",
    "OpenSSL": "pyOpenSSL",
    "PIL": "Pillow",
    "psycopg2": "psycopg2-binary",
    "pygments": "Pygments",
    "pymupdf": "PyMuPDF",
    "pydantic_core": "pydantic-core",
    "pydantic_settings": "pydantic-settings",
    "serial": "pyserial",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "telegram": "python-telegram-bot",
    "thefuzz": "thefuzz",
    "win32com": "pywin32",
    "win32api": "pywin32",
    "win32con": "pywin32",
    "win32gui": "pywin32",
    "yaml": "PyYAML",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "xlsxwriter": "XlsxWriter",
    "lxml": "lxml",
}

# Imports que, aunque no fallen al importarse, requieren un paquete extra en
# FastAPI/Pydantic. Se revisan en el grafo estático.
FASTAPI_FORM_IMPORTS = {"Form", "File", "UploadFile"}
STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", set()))


# ---------------------------------------------------------------------------
# Modelos de reporte
# ---------------------------------------------------------------------------

DependencyStatus = Literal[
    "installed",
    "failed",
    "missing",
    "skipped",
]


@dataclass
class DependencyAction:
    """Una instalación, intento fallido o dependencia detectada."""

    plugin: str
    spec: str
    status: DependencyStatus
    source: str
    module: Optional[str] = None
    message: str = ""
    command: Optional[list[str]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin": self.plugin,
            "spec": self.spec,
            "status": self.status,
            "source": self.source,
            "module": self.module,
            "message": self.message,
            "command": self.command,
        }


@dataclass
class MissingImport:
    module: str
    source: str
    spec: str
    reason: str


@dataclass
class FailureInfo:
    kind: str
    missing: list[str] = field(default_factory=list)
    hint: str = ""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off", ""}


def _read_text(path: Path) -> str:
    """Lee archivos que pueden estar en UTF-8, UTF-16 o latin-1."""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                return raw.decode(encoding)
            except UnicodeError:
                continue
    if raw.startswith(b"\xef\xbb\xbf"):
        try:
            return raw.decode("utf-8-sig")
        except UnicodeError:
            pass

    for encoding in ("utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeError:
            continue
    return ""


def _tail(text: str, limit: int = 1800) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return "..." + text[-limit:]


def _safe_int(value: Optional[str], default: int) -> int:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _invalidate_import_caches() -> None:
    """Hace visibles los paquetes recién instalados en el proceso actual."""
    importlib.invalidate_caches()
    try:
        importlib_metadata.MetadataPathFinder.invalidate_caches()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class PluginDependencyManager:
    """Resuelve e instala las dependencias externas de los plugins."""

    def __init__(
        self,
        project_root: Path,
        plugins_dir: Optional[Path] = None,
        execution_dir: Optional[Path] = None,
        enabled: Optional[bool] = None,
        auto_install_unknown: Optional[bool] = None,
        install_timeout: Optional[int] = None,
        python_executable: Optional[Path | str] = None,
        log: Optional[Any] = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.plugins_dir = (
            Path(plugins_dir).resolve()
            if plugins_dir is not None
            else (self.project_root / "plugins").resolve()
        )
        self.execution_dir = (
            Path(execution_dir).resolve()
            if execution_dir is not None
            else Path(EXECUTION_DIR).resolve()
        )

        self.enabled = (
            _env_flag(ENV_AUTO_INSTALL, True) if enabled is None else bool(enabled)
        )
        self.auto_install_unknown = (
            _env_flag(ENV_AUTO_INSTALL_UNKNOWN, True)
            if auto_install_unknown is None
            else bool(auto_install_unknown)
        )
        self.install_timeout = install_timeout or _safe_int(
            os.environ.get(ENV_INSTALL_TIMEOUT), DEFAULT_INSTALL_TIMEOUT
        )
        self.max_import_attempts = DEFAULT_MAX_IMPORT_ATTEMPTS
        self.log = log or self._default_log

        self._python_executable = (
            Path(python_executable) if python_executable else None
        )
        self._lock = threading.RLock()
        self._prepared: set[tuple[str, str]] = set()
        self._local_cache: dict[str, bool] = {}
        self._attempted_specs: dict[str, DependencyAction] = {}
        self._report_path = self.execution_dir / "data" / "plugin_dependencies.json"

        self.actions: list[DependencyAction] = []
        self.started_at = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Logging / reporte
    # ------------------------------------------------------------------

    def _default_log(self, message: str) -> None:
        text = f"[DEPS] {message}"
        try:
            print(text, flush=True)
        except UnicodeEncodeError:
            # Consolas Windows con code page antigua (cp1252) y emojis.
            safe = text.encode("ascii", errors="replace").decode("ascii")
            print(safe, flush=True)

    def _log(self, message: str) -> None:
        try:
            self.log(message)
        except Exception:
            self._default_log(message)

    def _record(self, action: DependencyAction) -> DependencyAction:
        self.actions.append(action)
        return action

    def get_actions(self) -> list[dict[str, Any]]:
        return [action.to_dict() for action in self.actions]

    def get_report(self) -> dict[str, Any]:
        installed = [a for a in self.actions if a.status == "installed"]
        failed = [a for a in self.actions if a.status == "failed"]
        missing = [a for a in self.actions if a.status == "missing"]
        skipped = [a for a in self.actions if a.status == "skipped"]
        return {
            "enabled": self.enabled,
            "auto_install_unknown": self.auto_install_unknown,
            "python_executable": str(self._resolve_python_executable()),
            "started_at": self.started_at.isoformat(),
            "summary": {
                "installed": len(installed),
                "failed": len(failed),
                "missing": len(missing),
                "skipped": len(skipped),
            },
            "actions": self.get_actions(),
        }

    def save_report(self) -> None:
        """Guarda el último reporte en data/plugin_dependencies.json."""
        try:
            self._report_path.parent.mkdir(parents=True, exist_ok=True)
            payload = self.get_report()
            payload["finished_at"] = datetime.now(timezone.utc).isoformat()
            self._report_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            self._log(f"No se pudo guardar el reporte de dependencias: {exc}")

    def print_summary(self) -> None:
        installed = [a for a in self.actions if a.status == "installed"]
        failed = [a for a in self.actions if a.status == "failed"]
        missing = [a for a in self.actions if a.status == "missing"]

        if not self.actions:
            self._log("Sin dependencias faltantes detectadas.")
            return

        if installed:
            self._log(f"Dependencias instaladas automáticamente: {len(installed)}")
            for action in installed:
                self._log(f"  [OK] {action.spec}  ({action.plugin})")
        if failed:
            self._log(f"[ERROR] Instalaciones fallidas: {len(failed)}")
            for action in failed:
                self._log(f"  - {action.spec}: {action.message}")
        if missing:
            self._log(f"Dependencias detectadas pero no instaladas: {len(missing)}")
            for action in missing:
                self._log(f"  - {action.spec}: {action.message}")

    # ------------------------------------------------------------------
    # Intérprete / pip
    # ------------------------------------------------------------------

    def _resolve_python_executable(self) -> Path:
        if self._python_executable is not None:
            return self._python_executable

        env_python = os.environ.get(ENV_VENV_PYTHON)
        if env_python:
            path = Path(env_python)
            if path.exists():
                self._python_executable = path
                return path

        # En desarrollo, el proceso normalmente ya corre dentro del venv.
        if not getattr(sys, "frozen", False):
            executable = Path(sys.executable)
            if executable.name.lower() in {"pythonw", "pythonw.exe"}:
                sibling = executable.with_name(
                    "python.exe" if os.name == "nt" else "python"
                )
                if sibling.exists():
                    executable = sibling
            self._python_executable = executable
            return executable

        # En un ejecutable PyInstaller, buscamos el venv junto a la app.
        for base in (self.execution_dir, self.project_root):
            for relative in (
                "venv/Scripts/python.exe",
                "venv/bin/python",
                ".venv/Scripts/python.exe",
                ".venv/bin/python",
            ):
                candidate = base / relative
                if candidate.exists():
                    self._python_executable = candidate
                    return candidate

        self._python_executable = Path(sys.executable)
        return self._python_executable

    def _pip_command(self, spec: str) -> list[str]:
        command = [
            str(self._resolve_python_executable()),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
        ]
        index_url = os.environ.get(ENV_PIP_INDEX_URL)
        if index_url:
            command.extend(["--index-url", index_url])
        command.append(spec)
        return command

    def _run_pip(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        creationflags = 0
        if os.name == "nt":
            # Evita que pythonw.exe abra una consola al instalar.
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.install_timeout,
            creationflags=creationflags,
            check=False,
        )

    # ------------------------------------------------------------------
    # Comprobación de requisitos
    # ------------------------------------------------------------------

    def _requirement_satisfied(self, spec: str, check_extras: bool = True) -> bool:
        spec = (spec or "").strip()
        if not spec:
            return True

        try:
            requirement = Requirement(spec)
        except InvalidRequirement:
            # URLs, VCS o requisitos no estándar: se dejan a pip.
            return False

        if requirement.marker is not None:
            try:
                if not requirement.marker.evaluate():
                    return True
            except Exception:
                pass

        return self._is_requirement_installed(requirement, check_extras=check_extras)

    def _is_requirement_installed(
        self, requirement: Requirement, check_extras: bool = True
    ) -> bool:
        try:
            installed_version = importlib_metadata.version(requirement.name)
        except importlib_metadata.PackageNotFoundError:
            return False
        except Exception:
            return False

        if requirement.specifier:
            try:
                if not requirement.specifier.contains(
                    installed_version, prereleases=True
                ):
                    return False
            except InvalidVersion:
                return False

        if check_extras and requirement.extras:
            if not self._extras_satisfied(requirement.name, requirement.extras):
                return False

        return True

    def _extras_satisfied(self, distribution: str, extras: Iterable[str]) -> bool:
        try:
            dist = importlib_metadata.distribution(distribution)
            requires = dist.requires or []
        except Exception:
            return False

        base_env = default_environment()
        extras = set(extras)

        for raw in requires:
            try:
                dependency = Requirement(raw)
            except InvalidRequirement:
                continue

            for extra in extras:
                env = dict(base_env)
                env["extra"] = extra
                try:
                    if dependency.marker is not None and not dependency.marker.evaluate(env):
                        continue
                except Exception:
                    continue

                if not self._is_requirement_installed(dependency, check_extras=False):
                    return False

        return True

    def _module_available(self, module: str) -> bool:
        module = (module or "").strip()
        if not module:
            return True
        try:
            return importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Lectura de dependencias declaradas
    # ------------------------------------------------------------------

    def _dependency_search_dirs(self, plugin_path: Path) -> list[Path]:
        """El plugin y sus ancestros hasta plugins/, sin incluir plugins/."""
        dirs: list[Path] = []
        current = plugin_path.resolve()
        plugins_root = self.plugins_dir.resolve()

        while current != plugins_root and plugins_root in current.parents:
            dirs.append(current)
            current = current.parent
        return dirs

    def collect_declared_dependencies(self, plugin_path: Path) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []
        seen_files: set[Path] = set()
        seen_specs: set[str] = set()

        def add(spec: str, source: str) -> None:
            spec = (spec or "").strip()
            if not spec:
                return
            key = spec.lower()
            if key in seen_specs:
                return
            seen_specs.add(key)
            results.append((spec, source))

        for directory in self._dependency_search_dirs(plugin_path):
            if not directory.is_dir():
                continue

            for pattern in ("requirements.txt", "requirements*.txt", "requirements/*.txt"):
                for path in sorted(directory.glob(pattern)):
                    if not path.is_file():
                        continue
                    lower_name = path.name.lower()
                    if any(
                        token in lower_name
                        for token in ("dev", "test", "lint", "doc", "ci", "example")
                    ):
                        continue
                    self._parse_requirements_file(path, add, seen_files)

            pyproject = directory / "pyproject.toml"
            if pyproject.is_file() and pyproject not in seen_files:
                seen_files.add(pyproject)
                self._parse_pyproject(pyproject, add)

            setup_cfg = directory / "setup.cfg"
            if setup_cfg.is_file() and setup_cfg not in seen_files:
                seen_files.add(setup_cfg)
                self._parse_setup_cfg(setup_cfg, add)

            for metadata_name in ("metadata.json", "plugin.json", "dependencies.json"):
                metadata_file = directory / metadata_name
                if metadata_file.is_file() and metadata_file not in seen_files:
                    seen_files.add(metadata_file)
                    self._parse_metadata_json(metadata_file, add)

        return results

    def _parse_requirements_file(
        self,
        path: Path,
        add: Any,
        seen_files: set[Path],
    ) -> None:
        path = path.resolve()
        if path in seen_files:
            return
        seen_files.add(path)

        for raw_line in _read_text(path).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            include_match = re.match(r"^(?:-r|--requirement)\s+(.+)$", line)
            if include_match:
                include = include_match.group(1).strip().strip("\"'")
                include_path = (path.parent / include).resolve()
                if include_path.is_file():
                    self._parse_requirements_file(include_path, add, seen_files)
                continue

            if line.startswith("-"):
                # -c, -e, --index-url, --find-links, etc.
                continue

            line = re.sub(r"\s+#.*$", "", line).strip()
            line = re.sub(r"\s+--hash(?:=|\s+)\S+", "", line).strip()
            if line:
                add(line, path.name)

    def _parse_pyproject(self, path: Path, add: Any) -> None:
        try:
            data = tomllib.loads(_read_text(path))
        except Exception:
            return

        project = data.get("project", {}) or {}
        for spec in project.get("dependencies", []) or []:
            if isinstance(spec, str):
                add(spec, f"{path.name} [project].dependencies")

        poetry = (
            (data.get("tool", {}) or {}).get("poetry", {}) or {}
        ).get("dependencies", {}) or {}
        for name, version in poetry.items():
            if str(name).lower() == "python":
                continue
            if isinstance(version, str):
                spec = name if version in ("*", "") else f"{name}{version}"
                add(spec, f"{path.name} [tool.poetry.dependencies]")
            elif isinstance(version, dict):
                if "path" in version:
                    continue
                if "git" in version:
                    add(
                        f"{name} @ git+{version['git']}",
                        f"{path.name} [tool.poetry.dependencies]",
                    )
                elif "version" in version:
                    spec_version = str(version["version"]).strip()
                    spec = name if spec_version in ("*", "") else f"{name}{spec_version}"
                    add(spec, f"{path.name} [tool.poetry.dependencies]")

    def _parse_setup_cfg(self, path: Path, add: Any) -> None:
        parser = configparser.ConfigParser()
        try:
            parser.read_string(_read_text(path))
            raw = parser.get("options", "install_requires", fallback="")
        except Exception:
            return

        if raw.strip().lower().startswith("file:"):
            return
        for line in raw.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                add(line, f"{path.name} install_requires")

    def _parse_metadata_json(self, path: Path, add: Any) -> None:
        try:
            data = json.loads(_read_text(path))
        except Exception:
            return

        keys = (
            "dependencies",
            "requirements",
            "pip_dependencies",
            "python_dependencies",
        )

        def extract(value: Any) -> Iterator[str]:
            if isinstance(value, str):
                for line in value.replace(",", "\n").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        yield line
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        yield item
                    elif isinstance(item, dict):
                        yield from extract(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    if key.lower() in {"pip", "python", "dependencies", "requirements"}:
                        yield from extract(item)

        if not isinstance(data, dict):
            return

        for key in keys:
            if key in data:
                for spec in extract(data[key]):
                    add(spec, f"{path.name} {key}")

    # ------------------------------------------------------------------
    # Grafo de imports del entry point
    # ------------------------------------------------------------------

    def _iter_python_children(self, path: Path) -> Iterator[Path]:
        if path.is_file() and path.suffix == ".py":
            yield path
            return
        if not path.is_dir():
            return
        for child in path.iterdir():
            if child.name in IGNORED_DIR_NAMES or child.name.startswith("."):
                continue
            if child.is_dir():
                yield from self._iter_python_children(child)
            elif child.suffix == ".py":
                yield child

    def _target_for_parts(self, base: Path, parts: list[Path | str]) -> Optional[Path]:
        if not parts:
            return None
        candidate = base.joinpath(*[str(part) for part in parts])
        module_file = candidate.with_suffix(".py")
        if module_file.is_file():
            return module_file
        init_file = candidate / "__init__.py"
        if init_file.is_file():
            return init_file
        return None

    def _is_local_module(
        self,
        module_top: str,
        plugin_path: Path,
        current_file: Optional[Path] = None,
    ) -> bool:
        module_top = module_top.split(".")[0]
        current_dir = str(current_file.parent.resolve()) if current_file else ""
        cache_key = f"{plugin_path}|{current_dir}|{module_top}"
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]

        candidates = [self.project_root / module_top, self.project_root / f"{module_top}.py"]
        plugins_root = self.plugins_dir.resolve()

        starts = [plugin_path.resolve()]
        if current_file is not None:
            starts.append(current_file.parent.resolve())

        visited_roots: set[Path] = set()
        for start in starts:
            current = start
            # Solo se consideran padres que pertenezcan al árbol de plugins.
            if current != plugins_root and plugins_root not in current.parents:
                continue
            while True:
                if current in visited_roots:
                    break
                visited_roots.add(current)
                candidates.append(current / module_top)
                candidates.append(current / f"{module_top}.py")
                if current == plugins_root or plugins_root not in current.parents:
                    break
                current = current.parent

        is_local = any(candidate.exists() for candidate in candidates)
        self._local_cache[cache_key] = is_local
        return is_local

    def _failing_files(self, exc: BaseException) -> list[Path]:
        """Archivos del plugin presentes en el traceback de la excepción."""
        files: list[Path] = []
        tb = exc.__traceback__
        while tb is not None:
            filename = tb.tb_frame.f_code.co_filename
            if filename and not filename.startswith("<"):
                path = Path(filename)
                if path.suffix == ".py":
                    files.append(path)
            tb = tb.tb_next
        return files

    def _is_local_in_context(
        self,
        module_top: str,
        plugin_path: Optional[Path],
        exc: Optional[BaseException] = None,
    ) -> bool:
        if plugin_path is not None and self._is_local_module(module_top, plugin_path):
            return True
        if exc is not None:
            for failing_file in self._failing_files(exc):
                if plugin_path is not None and self._is_local_module(
                    module_top, plugin_path, failing_file
                ):
                    return True
                if self._is_local_module(module_top, failing_file.parent, failing_file):
                    return True
        return False

    def _resolve_relative_targets(
        self,
        current_file: Path,
        level: int,
        module: Optional[str],
        names: list[ast.alias],
    ) -> list[Path]:
        base = current_file.parent
        for _ in range(max(0, level - 1)):
            base = base.parent

        targets: list[Path] = []
        parts = module.split(".") if module else []

        if parts:
            target = self._target_for_parts(base, parts)
            if target is not None:
                targets.append(target)

            for alias in names:
                child = self._target_for_parts(
                    base, parts + alias.name.split(".")
                )
                if child is not None:
                    targets.append(child)
        else:
            for alias in names:
                target = self._target_for_parts(base, alias.name.split("."))
                if target is not None:
                    targets.append(target)

        return targets

    def _resolve_absolute_local_target(
        self,
        module: str,
        plugin_path: Path,
        current_file: Optional[Path] = None,
    ) -> Optional[Path]:
        if not module:
            return None
        parts = module.split(".")

        plugins_root = self.plugins_dir.resolve()
        starts = [plugin_path.resolve()]
        if current_file is not None:
            starts.insert(0, current_file.parent.resolve())

        roots: list[Path] = []
        visited_roots: set[Path] = set()
        for start in starts:
            current = start
            if current != plugins_root and plugins_root not in current.parents:
                continue
            while True:
                if current in visited_roots:
                    break
                visited_roots.add(current)
                roots.append(current)
                if current == plugins_root or plugins_root not in current.parents:
                    break
                current = current.parent

        for root in roots:
            target = self._target_for_parts(root, parts)
            if target is not None:
                return target
        return None

    def _distribution_for_module(self, module: str) -> str:
        top = module.split(".")[0]
        mapped = IMPORT_TO_DISTRIBUTION.get(top) or IMPORT_TO_DISTRIBUTION.get(
            top.lower()
        )
        if mapped:
            return mapped

        try:
            packages = importlib_metadata.packages_distributions()
            distributions = packages.get(top) or packages.get(top.lower())
            if distributions:
                return canonicalize_name(distributions[0])
        except Exception:
            pass

        return top.replace("_", "-")

    def _record_missing(
        self,
        missing: dict[str, MissingImport],
        module: str,
        current_file: Path,
        plugin_path: Path,
        reason: str,
    ) -> None:
        module = (module or "").strip()
        if not module:
            return

        top = module.split(".")[0]
        if top in STDLIB_MODULES or top in sys.builtin_module_names:
            return
        if self._is_local_module(top, plugin_path, current_file):
            return
        if self._module_available(top):
            return

        if not self.auto_install_unknown and top not in IMPORT_TO_DISTRIBUTION:
            return

        distribution = self._distribution_for_module(module)
        key = canonicalize_name(distribution)
        if key in missing:
            return

        try:
            relative = current_file.relative_to(self.plugins_dir)
        except ValueError:
            relative = current_file

        missing[key] = MissingImport(
            module=module,
            source=str(relative),
            spec=distribution,
            reason=reason,
        )

    def scan_entry_imports(
        self, plugin_path: Path, entry_file: Path
    ) -> list[MissingImport]:
        if not entry_file.is_file():
            return []

        pending: list[Path] = [entry_file.resolve()]
        visited: set[Path] = set()
        missing: dict[str, MissingImport] = {}

        while pending:
            current_file = pending.pop()
            if current_file in visited:
                continue
            visited.add(current_file)

            try:
                source = _read_text(current_file)
                tree = ast.parse(source, filename=str(current_file))
            except (OSError, SyntaxError, ValueError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._record_missing(
                            missing,
                            alias.name,
                            current_file,
                            plugin_path,
                            f"import {alias.name}",
                        )

                elif isinstance(node, ast.ImportFrom):
                    if node.module == "pydantic" and any(
                        alias.name == "EmailStr" for alias in node.names
                    ):
                        if not self._module_available("email_validator"):
                            missing.setdefault(
                                "email-validator",
                                MissingImport(
                                    module="email_validator",
                                    source=str(
                                        current_file.relative_to(self.plugins_dir)
                                        if self.plugins_dir in current_file.parents
                                        else current_file
                                    ),
                                    spec="email-validator>=2.0.0",
                                    reason="EmailStr de Pydantic",
                                ),
                            )

                    if (
                        node.module == "fastapi"
                        and any(
                            alias.name in FASTAPI_FORM_IMPORTS
                            for alias in node.names
                        )
                        and not self._module_available("multipart")
                    ):
                        missing.setdefault(
                            "python-multipart",
                            MissingImport(
                                module="multipart",
                                source=str(
                                    current_file.relative_to(self.plugins_dir)
                                    if self.plugins_dir in current_file.parents
                                    else current_file
                                ),
                                spec="python-multipart",
                                reason="Form/File/UploadFile de FastAPI",
                            ),
                        )

                    if node.level:
                        for target in self._resolve_relative_targets(
                            current_file, node.level, node.module, list(node.names)
                        ):
                            if target not in visited:
                                pending.append(target)
                    else:
                        module = node.module or ""
                        local_target = self._resolve_absolute_local_target(
                            module, plugin_path, current_file
                        )
                        if local_target is not None:
                            if local_target not in visited:
                                pending.append(local_target)
                        else:
                            self._record_missing(
                                missing,
                                module,
                                current_file,
                                plugin_path,
                                f"from {module} import ...",
                            )

        return list(missing.values())

    # ------------------------------------------------------------------
    # Instalación
    # ------------------------------------------------------------------

    def _install_spec(
        self,
        spec: str,
        plugin: str,
        source: str,
        module: Optional[str] = None,
    ) -> DependencyAction:
        spec = (spec or "").strip()
        if not spec:
            return self._record(
                DependencyAction(
                    plugin=plugin,
                    spec=spec,
                    status="skipped",
                    source=source,
                    module=module,
                    message="Especificación vacía.",
                )
            )

        key = spec.lower()
        with self._lock:
            previous = self._attempted_specs.get(key)
            if previous is not None:
                return previous

            if not self.enabled:
                return self._record(
                    DependencyAction(
                        plugin=plugin,
                        spec=spec,
                        status="missing",
                        source=source,
                        module=module,
                        message=(
                            "Instalación automática desactivada "
                            f"({ENV_AUTO_INSTALL}=0)."
                        ),
                    )
                )

            command = self._pip_command(spec)
            self._log(
                f"Instalando dependencia faltante '{spec}' "
                f"para el plugin '{plugin}' ({source})..."
            )

            started = time.monotonic()
            try:
                result = self._run_pip(command)
                output = _tail(result.stdout or "")
                elapsed = time.monotonic() - started

                if result.returncode == 0:
                    _invalidate_import_caches()
                    action = DependencyAction(
                        plugin=plugin,
                        spec=spec,
                        status="installed",
                        source=source,
                        module=module,
                        message=f"Instalado en {elapsed:.1f}s.",
                        command=command,
                    )
                    self._attempted_specs[key] = action
                    self._record(action)
                    self._log(f"[OK] Instalado '{spec}' para '{plugin}'.")
                    return action

                action = DependencyAction(
                    plugin=plugin,
                    spec=spec,
                    status="failed",
                    source=source,
                    module=module,
                    message=(
                        f"pip terminó con código {result.returncode}. "
                        f"Salida: {output}"
                    ),
                    command=command,
                )
                self._attempted_specs[key] = action
                self._record(action)
                self._log(f"[ERROR] No se pudo instalar '{spec}': {output}")
                return action

            except subprocess.TimeoutExpired:
                action = DependencyAction(
                    plugin=plugin,
                    spec=spec,
                    status="failed",
                    source=source,
                    module=module,
                    message=(
                        f"Tiempo de espera agotado tras {self.install_timeout}s."
                    ),
                    command=command,
                )
                self._attempted_specs[key] = action
                self._record(action)
                self._log(f"[ERROR] Timeout instalando '{spec}'.")
                return action

            except Exception as exc:
                action = DependencyAction(
                    plugin=plugin,
                    spec=spec,
                    status="failed",
                    source=source,
                    module=module,
                    message=f"{type(exc).__name__}: {exc}",
                    command=command,
                )
                self._attempted_specs[key] = action
                self._record(action)
                self._log(f"[ERROR] Error instalando '{spec}': {exc}")
                return action

    def _install_missing_imports(
        self,
        plugin: str,
        missing: Iterable[MissingImport],
    ) -> list[DependencyAction]:
        actions: list[DependencyAction] = []
        for item in missing:
            if self._requirement_satisfied(item.spec):
                continue
            actions.append(
                self._install_spec(
                    item.spec,
                    plugin=plugin,
                    source=f"{item.reason} ({item.source})",
                    module=item.module,
                )
            )
        return actions

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def ensure_plugin_dependencies(
        self,
        plugin_path: Path,
        entry_file: Optional[Path] = None,
        plugin_name: Optional[str] = None,
    ) -> list[DependencyAction]:
        """Revisa declaraciones e imports de un plugin antes de importarlo."""
        plugin_path = Path(plugin_path).resolve()
        plugin = plugin_name or plugin_path.name
        entry_key = str(entry_file.resolve()) if entry_file else ""

        with self._lock:
            prepared_key = (str(plugin_path), entry_key)
            if prepared_key in self._prepared:
                return []
            self._prepared.add(prepared_key)

            actions: list[DependencyAction] = []

            for spec, source in self.collect_declared_dependencies(plugin_path):
                if self._requirement_satisfied(spec):
                    continue
                actions.append(
                    self._install_spec(
                        spec,
                        plugin=plugin,
                        source=f"declarada en {source}",
                    )
                )

            if entry_file is not None and Path(entry_file).is_file():
                missing = self.scan_entry_imports(plugin_path, Path(entry_file))
                actions.extend(self._install_missing_imports(plugin, missing))

            return actions

    def discover_entry_points(self, plugins_dir: Optional[Path] = None) -> list[tuple[Path, Path]]:
        """Descubre plugins con la misma convención que PluginManager."""
        root = Path(plugins_dir or self.plugins_dir).resolve()
        entries: list[tuple[Path, Path]] = []
        if not root.is_dir():
            return entries

        excluded = IGNORED_DIR_NAMES | {
            "data",
            "background_processes",
            "backgroundProcesses",
            "fails",
        }

        for path in root.rglob("*"):
            if not path.is_dir():
                continue
            if path.name in excluded or path.name.startswith((".", "_")):
                continue
            if any(
                part in excluded or part.startswith((".", "_"))
                for part in path.relative_to(root).parts
            ):
                continue

            candidates = [path / f"{path.name}.py", path / "main.py"]
            for candidate in candidates:
                if candidate.is_file():
                    entries.append((path, candidate))
                    break
        return entries

    def preflight(self, plugins_dir: Optional[Path] = None) -> list[DependencyAction]:
        """
        Revisa todos los plugins antes de que PluginManager los importe.
        Devuelve las acciones de instalación realizadas.
        """
        if not _env_flag(ENV_PREFLIGHT, True):
            return []

        actions: list[DependencyAction] = []
        for plugin_path, entry_file in self.discover_entry_points(plugins_dir):
            # Un nombre inválido no puede importarse; PluginManager lo reportará
            # como error estructural, no como dependencia faltante.
            if not plugin_path.name.isidentifier() or not entry_file.stem.isidentifier():
                continue
            try:
                actions.extend(
                    self.ensure_plugin_dependencies(
                        plugin_path, entry_file, plugin_name=plugin_path.name
                    )
                )
            except Exception as exc:
                self._log(
                    f"No se pudo revisar dependencias de {plugin_path.name}: {exc}"
                )
        return actions

    # ------------------------------------------------------------------
    # Extracción de dependencias desde excepciones
    # ------------------------------------------------------------------

    _MISSING_MODULE_RE = re.compile(r"No module named ['\"]([^'\"]+)['\"]")
    _PIP_INSTALL_RE = re.compile(
        r"pip\s+install\s+(?:--?[A-Za-z0-9_.-]+(?:[=\s]+[^\s'\"]+)?\s+)*"
        r"['\"]?([A-Za-z0-9_.\-]+(?:\[[A-Za-z0-9_,.\-]+\])?"
        r"(?:[<>=!~]=?[^\s'\"]+)?)['\"]?"
    )
    _IS_NOT_INSTALLED_RE = re.compile(
        r"['\"]?([A-Za-z0-9_.\-]+)['\"]?\s+is\s+not\s+installed",
        re.IGNORECASE,
    )
    _OPTIONAL_DEP_RE = re.compile(
        r"Missing optional dependency ['\"]([^'\"]+)['\"]",
        re.IGNORECASE,
    )

    def _walk_exception_chain(self, exc: BaseException) -> Iterator[BaseException]:
        seen: set[int] = set()
        stack: list[BaseException] = [exc]
        while stack:
            current = stack.pop()
            if id(current) in seen:
                continue
            seen.add(id(current))
            yield current

            try:
                from builtins import BaseExceptionGroup as BaseExceptionGroupType
            except ImportError:  # Python < 3.11
                BaseExceptionGroupType = None  # type: ignore[assignment,misc]

            if BaseExceptionGroupType is not None and isinstance(
                current, BaseExceptionGroupType
            ):
                stack.extend(current.exceptions)  # type: ignore[attr-defined]
            if current.__cause__ is not None:
                stack.append(current.__cause__)
            if current.__context__ is not None:
                stack.append(current.__context__)

    def extract_missing_dependencies(
        self, exc: BaseException
    ) -> tuple[list[str], list[str]]:
        """
        Devuelve (specs_de_pip, modulos_faltantes) detectados en la excepción.
        """
        specs: list[str] = []
        modules: list[str] = []

        def distribution_name(spec: str) -> str:
            try:
                return canonicalize_name(Requirement(spec).name)
            except InvalidRequirement:
                return spec.lower()

        def add_spec(spec: str) -> None:
            spec = (spec or "").strip().strip("\"'")
            if not spec:
                return
            name = distribution_name(spec)
            for existing in specs:
                if distribution_name(existing) == name:
                    # Preferir la especificación con restricciones de versión.
                    if "==" not in existing and "==" in spec:
                        specs[specs.index(existing)] = spec
                    return
            specs.append(spec)

        def add_module(module: str) -> None:
            module = (module or "").strip()
            if module and module not in modules:
                modules.append(module)

        for current in self._walk_exception_chain(exc):
            text = str(current)
            lowered = text.lower()

            if isinstance(current, ModuleNotFoundError):
                add_module(current.name or "")

            match = self._MISSING_MODULE_RE.search(text)
            if match:
                add_module(match.group(1))

            if "email-validator is not installed" in lowered or (
                "email_validator" in lowered and "not installed" in lowered
            ):
                add_spec("email-validator>=2.0.0")

            if "python-multipart" in lowered and (
                "not installed" in lowered or "pip install" in lowered
            ):
                add_spec("python-multipart")

            for match in self._PIP_INSTALL_RE.finditer(text):
                candidate = match.group(1).strip()
                # No intentar instalar el propio proyecto ni extras genéricos.
                if candidate.lower() in {"pydantic[email]"} and any(
                    spec.startswith("email-validator") for spec in specs
                ):
                    continue
                add_spec(candidate)

            for match in self._IS_NOT_INSTALLED_RE.finditer(text):
                candidate = match.group(1).strip()
                if candidate.lower() not in {"it", "this", "module", "package"}:
                    add_spec(candidate)

            for match in self._OPTIONAL_DEP_RE.finditer(text):
                candidate = match.group(1).strip()
                if candidate:
                    add_spec(candidate)

        return specs, modules

    def resolve_import_failure(
        self,
        plugin_path: Optional[Path],
        exc: BaseException,
        plugin_name: str,
    ) -> list[DependencyAction]:
        """
        Instala lo que falte según la excepción. Devuelve las acciones que
        realmente instalaron algo (para decidir si vale la pena reintentar).
        """
        specs, modules = self.extract_missing_dependencies(exc)
        actions: list[DependencyAction] = []

        def attempt(spec: str, source: str, module: str | None = None) -> None:
            before = len(self.actions)
            action = self._install_spec(
                spec,
                plugin=plugin_name,
                source=source,
                module=module,
            )
            # Solo cuenta como "nueva instalación" si realmente se intentó
            # ahora. Así no se reintenta infinitamente el mismo fallo.
            if action.status == "installed" and len(self.actions) > before:
                actions.append(action)

        for module in modules:
            top = module.split(".")[0]

            if self._is_local_in_context(top, plugin_path, exc):
                self._log(
                    f"El plugin '{plugin_name}' referencia un módulo local "
                    f"inexistente o no importable: {module}. "
                    "No se intentará instalar."
                )
                continue

            if self._module_available(top):
                # El paquete existe, pero falta un submódulo: es un problema
                # de código/versión, no una dependencia ausente.
                continue

            distribution = self._distribution_for_module(module)
            attempt(
                distribution,
                f"ModuleNotFoundError: {module}",
                module=module,
            )

        for spec in specs:
            if self._requirement_satisfied(spec):
                continue
            attempt(spec, "ImportError durante la carga del plugin")

        return actions

    # ------------------------------------------------------------------
    # Diagnóstico
    # ------------------------------------------------------------------

    def classify_failure(
        self, exc: BaseException, plugin_path: Optional[Path]
    ) -> FailureInfo:
        specs, modules = self.extract_missing_dependencies(exc)
        missing = list(dict.fromkeys([*modules, *specs]))

        local_missing = [
            module
            for module in modules
            if self._is_local_in_context(module.split(".")[0], plugin_path, exc)
        ]

        if local_missing:
            return FailureInfo(
                kind="plugin_structure",
                missing=local_missing,
                hint=(
                    "El plugin referencia un módulo local que no existe o no "
                    "es importable desde sys.path. Revisa imports relativos, "
                    f"nombres de archivo y rutas ({', '.join(local_missing)})."
                ),
            )

        if missing:
            return FailureInfo(
                kind="missing_dependency",
                missing=missing,
                hint=(
                    "No se pudieron resolver todas las dependencias. "
                    "Revisa el reporte de dependencias y el log de pip."
                ),
            )

        return FailureInfo(
            kind="unknown",
            missing=[],
            hint="Error no relacionado con una dependencia faltante.",
        )
