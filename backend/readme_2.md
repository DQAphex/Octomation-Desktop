# 🚀 Guía de Inicio Rápido para el Proyecto

Esta guía contiene las instrucciones paso a paso para configurar el entorno de desarrollo, instalar dependencias y ejecutar la aplicación en cualquier equipo con Python.

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de contar con los siguientes elementos instalados en el equipo:

1. **Python 3.10 o superior**:
   * Descargar de [python.org](https://www.python.org/downloads/).
   * ⚠️ **IMPORTANTE (Windows)**: Durante la instalación, marca obligatoriamente la casilla **"Add Python to PATH"**.
2. **Git** (Opcional, si clonas el repositorio directamente).
3. **Tesseract OCR** (Requerido solo para procesamiento de escaneos PDF con OCR).

---

## 💻 Paso 1: Clonar o Extraer el Proyecto

Si recibiste el proyecto en un archivo comprimido (`.zip`), extráelo en una ruta local corta sin espacios ni caracteres especiales.

* **Ruta recomendada**: `C:\Proyectos\hola` o `C:\Users\<TuUsuario>\hola`

Abre una consola de comandos (**PowerShell** o **Terminal**) y navega hasta la carpeta del proyecto:

```powershell
cd "C:\Ruta\De\Tu\Proyecto\hola"

```

---

## 🐍 Paso 2: Crear el Entorno Virtual Python

El entorno virtual aislará las librerías del proyecto de la instalación global del sistema.

Ejecuta en la terminal:

```powershell
python -m venv venv

```

Esto creará una carpeta llamada `venv/` dentro de la raíz de tu proyecto.

---

## 🔓 Paso 3: Activar el Entorno Virtual

Debes activar el entorno virtual para que los comandos de Python y `pip` apunten al entorno aislado.

### En Windows (PowerShell):

```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& ".\venv\Scripts\Activate.ps1")

```

> 💡 **Nota**: Verás que la consola ahora muestra el prefijo `(venv)` al inicio de la línea de comandos.

### En Windows (CMD / Símbolo del Sistema):

```cmd
.\venv\Scripts\activate.bat

```

### En macOS / Linux:

```bash
source venv/bin/activate

```

---

## 📦 Paso 4: Instalar las Dependencias

Con el entorno virtual activo `(venv)`, actualiza `pip` e instala todas las librerías necesarias ejecutando:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt

```

---

## ⚙️ Paso 5: Configuración de Entorno (Opcional - OCR Tesseract)

Si el sistema procesará lectura de PDFs escaneados mediante OCR:

1. Descarga e instala Tesseract OCR para Windows.
2. Verifica que el ejecutable esté accesible en la ruta por defecto:
`C:\Program Files\Tesseract-OCR\tesseract.exe`
3. O agrega la ruta del ejecutable a la variable de entorno `PATH` del sistema.

---

## ▶️ Paso 6: Ejecutar la Aplicación

Una vez completada la instalación, inicia el servidor principal del proyecto ejecutando:

```powershell
python main.py

```

### Verificación del Inicio:

* La consola desplegará los logs iniciales indicando que el servidor local está corriendo.
* Abre tu navegador web e ingresa a la siguiente dirección:
`http://127.0.0.1:8000`

---

## ❓ Solución de Problemas Comunes

| Error / Problema | Causa Posible | Solución |
| --- | --- | --- |
| `ScriptExecution` en PowerShell | Política de ejecución restringida | Ejecuta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` antes de activar. |
| `ModuleNotFoundError` | El entorno virtual no está activo o faltan librerías | Asegúrate de ver `(venv)` en la terminal y vuelve a ejecutar `pip install -r requirements.txt`. |
| `tesseract is not installed` | Falta el motor OCR binario | Instala Tesseract OCR en Windows y asegúrate de agregar la ruta en `PATH`. |

```