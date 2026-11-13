# Dependencias automáticas de plugins

La aplicación revisa las dependencias de los plugins **al iniciar FastAPI**
(`PluginManager.discover_and_load()`), antes de importar cada router.

Si falta una librería, el sistema intenta instalarla en el mismo entorno virtual
que está ejecutando la aplicación:

```text
<venv>\Scripts\python.exe -m pip install <paquete>
```

Después de instalar, reintenta la importación del plugin. Si aun así falla, el
plugin queda registrado en la lista de errores y se muestra el motivo en el log
y en el endpoint `/plugins/status`.

## Cómo declara sus dependencias un plugin

El sistema busca dependencias en la carpeta del plugin y en sus carpetas padre
(hasta `plugins/`, sin incluirla). Formatos soportados:

### `requirements.txt`

```text
pandas>=2.2
httpx
python-dotenv
```

También se aceptan `requirements/*.txt` y archivos `requirements-*.txt`.
Se ignoran automáticamente los archivos de desarrollo/test
(`requirements-dev.txt`, `requirements-test.txt`, etc.).

### `pyproject.toml`

```toml
[project]
name = "mi-plugin"
version = "0.1.0"
dependencies = [
  "pandas>=2.2",
  "httpx",
]
```

También se leen dependencias de Poetry en `[tool.poetry.dependencies]`.

### `metadata.json` / `plugin.json` / `dependencies.json`

```json
{
  "dependencies": [
    "pandas>=2.2",
    "httpx"
  ]
}
```

### `setup.cfg`

```ini
[options]
install_requires =
    pandas>=2.2
    httpx
```

## Detección por imports

Si el plugin no declara dependencias, el sistema analiza el grafo de imports
desde el archivo de entrada del plugin (`<carpeta>.py` o `main.py`). Solo revisa
los módulos que realmente se importan al cargar el plugin, no todo el árbol de
carpetas.

También detecta casos especiales que no fallan con `ModuleNotFoundError`, por
ejemplo:

- `EmailStr` de Pydantic requiere `email-validator`.
- `Form`, `File` o `UploadFile` de FastAPI requieren `python-multipart`.

Y durante la importación captura:

- `ModuleNotFoundError`
- `ImportError` con mensajes como `"X is not installed, run pip install ..."`
- Errores de dependencias opcionales de Pydantic/FastAPI

## Diagnóstico

- Log de arranque: muestra cada instalación, reintento o error.
- `data/plugin_dependencies.json`: último reporte de dependencias.
- `GET /plugins/status`: estado de plugins cargados, fallidos y dependencias.
- `GET /loaded-routers`: mantiene el listado anterior y agrega
  `failed_plugins` y `dependencies`.

Los errores estructurales (por ejemplo, una carpeta con guiones o un import
relativo a un archivo que no existe) se reportan como `plugin_structure` y no
se intentan "arreglar" instalando paquetes desde PyPI.

## Variables de entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `OCTOMATION_AUTO_INSTALL_DEPS` | `1` | Activa/desactiva la instalación automática. |
| `OCTOMATION_AUTO_INSTALL_UNKNOWN` | `1` | Permite inferir el nombre PyPI de imports no mapeados. |
| `OCTOMATION_VENV_PYTHON` | auto | Fuerza el Python usado para `pip`. |
| `OCTOMATION_DEP_INSTALL_TIMEOUT` | `300` | Timeout de cada `pip install` en segundos. |
| `OCTOMATION_DEP_PREFLIGHT` | `1` | Revisa dependencias antes de cargar los plugins. |
| `OCTOMATION_PIP_INDEX_URL` | — | Índice alternativo para pip. |

Para desactivar la instalación automática:

```powershell
$env:OCTOMATION_AUTO_INSTALL_DEPS = "0"
```

> **Nota de seguridad:** instalar dependencias de un plugin de GitHub implica
> ejecutar `pip install` de paquetes de terceros. Instala solo plugins de
> repositorios confiables o desactiva la instalación automática y revisa sus
> dependencias manualmente.
