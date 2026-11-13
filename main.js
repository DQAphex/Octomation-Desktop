const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');
const https = require('https');
const crypto = require('crypto');
const AdmZip = require('adm-zip');

let mainWindow;
let fastApiProcess = null;
let currentPort = null;
let fastApiPid = null;
let isStartingFastAPI = false;
let ensureVenvPromise = null;

ipcMain.on('window:minimize', () => {
  mainWindow?.minimize();
});

ipcMain.on('window:maximize', () => {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
});

ipcMain.on('window:close', () => {
  mainWindow?.close();
});

function getBackendPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend');
  }

  return path.join(__dirname, 'backend');
}

// ---------------------------------------------------------------------------
// Entorno virtual de Python (se crea en el primer arranque dentro de userData)
// ---------------------------------------------------------------------------

function getVenvDir() {
  return path.join(app.getPath('userData'), 'venv');
}

function getVenvPython() {
  const venvDir = getVenvDir();

  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true, ...options });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => {
      stdout += data;
      console.log(`[SETUP] ${data.toString().trimEnd()}`);
    });

    child.stderr.on('data', (data) => {
      stderr += data;
      console.log(`[SETUP] ${data.toString().trimEnd()}`);
    });

    child.on('error', reject);

    child.on('close', (code) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(
          `"${command} ${args.join(' ')}" terminó con código ${code}\n${stderr.slice(-1500)}`
        ));
      }
    });
  });
}

async function findSystemPython() {
  const candidates = process.platform === 'win32'
    ? [['py', ['-3']], ['python', []], ['python3', []]]
    : [['python3', []], ['python', []]];

  for (const [cmd, prefixArgs] of candidates) {
    try {
      const out = await runCommand(cmd, [
        ...prefixArgs,
        '-c',
        'import sys; print("%d.%d" % sys.version_info[:2])'
      ]);

      const [major, minor] = out.trim().split('.').map(Number);

      if (major === 3 && minor >= 9) {
        console.log(`[SETUP] Python del sistema: ${cmd} ${prefixArgs.join(' ')} (${major}.${minor})`);
        return { cmd, prefixArgs };
      }
    } catch (error) {
      // Probar el siguiente candidato
    }
  }

  throw new Error(
    'No se encontró Python 3.9 o superior. Instálalo desde python.org ' +
    '(marcando "Add Python to PATH") y vuelve a abrir la aplicación.'
  );
}

function sendSetupStatus(message) {
  console.log(`[SETUP] ${message}`);

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('fastapi-setup', message);
  }
}

async function ensureVenvInternal() {
  const backendPath = getBackendPath();
  const reqFile = path.join(backendPath, 'requirements.txt');

  if (!fs.existsSync(reqFile)) {
    throw new Error(`No se encontró requirements.txt: ${reqFile}`);
  }

  const venvDir = getVenvDir();
  const venvPython = getVenvPython();
  const stampFile = path.join(venvDir, '.requirements.hash');

  const reqHash = crypto
    .createHash('sha256')
    .update(fs.readFileSync(reqFile))
    .digest('hex');

  const venvReady =
    fs.existsSync(venvPython) &&
    fs.existsSync(stampFile) &&
    fs.readFileSync(stampFile, 'utf8') === reqHash;

  if (venvReady) {
    return venvPython;
  }

  if (!fs.existsSync(venvPython)) {
    sendSetupStatus('Creando entorno de Python (solo la primera vez)...');

    fs.rmSync(venvDir, { recursive: true, force: true });
    fs.mkdirSync(path.dirname(venvDir), { recursive: true });

    const python = await findSystemPython();

    await runCommand(python.cmd, [
      ...python.prefixArgs,
      '-m',
      'venv',
      venvDir
    ]);
  }

  sendSetupStatus('Instalando dependencias del backend...');

  await runCommand(
    venvPython,
    ['-m', 'pip', 'install', '-r', reqFile],
    {
      cwd: backendPath,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8'
      }
    }
  );

  fs.writeFileSync(stampFile, reqHash);
  sendSetupStatus('Entorno listo.');

  return venvPython;
}

// Evita que dos llamadas simultáneas (arranque + instalación de plugin)
// creen el venv al mismo tiempo.
function ensureVenv() {
  if (!ensureVenvPromise) {
    ensureVenvPromise = ensureVenvInternal().finally(() => {
      ensureVenvPromise = null;
    });
  }

  return ensureVenvPromise;
}

// ---------------------------------------------------------------------------
// FastAPI
// ---------------------------------------------------------------------------

function isServerAlive(port) {
  return new Promise((resolve) => {
    const req = http.get(
      `http://127.0.0.1:${port}/health`,
      (res) => {
        res.resume();
        resolve(res.statusCode === 200);
      }
    );

    req.on('error', () => resolve(false));

    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function findRunningServer() {
  if (await isServerAlive(8000)) {
    console.log('[Electron] Servidor FastAPI ya está en ejecución en puerto 8000');
    return 8000;
  }

  return null;
}

async function startFastAPI() {
  if (isStartingFastAPI) {
    console.log('[Electron] El servidor ya está iniciando.');
    return;
  }

  if (fastApiProcess && fastApiPid) {
    console.log('[Electron] Ya existe un proceso FastAPI administrado por Electron.');
    return;
  }

  isStartingFastAPI = true;

  try {
    const backendPath = getBackendPath();
    const mainPyPath = path.join(backendPath, 'main.py');

    if (!fs.existsSync(backendPath)) {
      throw new Error(`No se encontró la carpeta backend: ${backendPath}`);
    }

    if (!fs.existsSync(mainPyPath)) {
      throw new Error(`No se encontró el archivo de entrada: ${mainPyPath}`);
    }

    const port = 8000;

    // Crea el venv si no existe (o reinstala dependencias si cambió requirements.txt)
    const command = await ensureVenv();

    const args = [
      '-m',
      'uvicorn',
      'main:app',
      '--host',
      '127.0.0.1',
      '--port',
      String(port)
    ];

    console.log(`[Electron] Iniciando FastAPI: ${command} ${args.join(' ')}`);
    console.log(`[Electron] Directorio de trabajo: ${backendPath}`);

    currentPort = port;

    const child = spawn(command, args, {
      cwd: backendPath,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8'
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true
    });

    fastApiProcess = child;

    child.on('spawn', () => {
      fastApiPid = child.pid ?? null;
      console.log(`[FastAPI] Proceso iniciado. PID: ${fastApiPid}`);
    });

    child.stdout.on('data', (data) => {
      console.log(`[FastAPI] ${data.toString().trimEnd()}`);
    });

    child.stderr.on('data', (data) => {
      console.error(`[FastAPI ERR] ${data.toString().trimEnd()}`);
    });

    child.on('error', (error) => {
      console.error('[Electron] No se pudo ejecutar Python/Uvicorn:', error);

      if (fastApiProcess === child) {
        fastApiProcess = null;
        fastApiPid = null;
      }

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('fastapi-status', {
          running: false,
          error: error.message
        });
      }
    });

    child.on('close', (code) => {
      console.log(`[FastAPI] Proceso cerrado. Código: ${code}`);

      if (fastApiProcess === child) {
        fastApiProcess = null;
        fastApiPid = null;
      }

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('fastapi-status', {
          running: false
        });
        mainWindow.webContents.send('fastapi-pid', null);
      }
    });

    // Esperar hasta 15 segundos a que FastAPI responda.
    for (let attempt = 0; attempt < 30; attempt++) {
      if (fastApiProcess !== child || child.exitCode !== null) {
        break;
      }

      if (await isServerAlive(port)) {
        console.log(`[FastAPI] Servidor disponible en el puerto ${port}`);
        sendPortToRenderer(port);
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 500));
    }

    if (fastApiProcess === child && !(await isServerAlive(port))) {
      const message = 'FastAPI no respondió a tiempo en el puerto 8000.';
      console.error(`[Electron] ${message}`);

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('fastapi-status', {
          running: false,
          error: message
        });
      }
    }
  } finally {
    isStartingFastAPI = false;
  }
}

function stopFastAPI() {
  if (fastApiProcess && fastApiPid) {
    const child = fastApiProcess;
    const pidToLog = fastApiPid;

    console.log(`[Electron] Apagando FastAPI. PID: ${pidToLog}`);

    try {
      child.kill();

      fastApiProcess = null;
      fastApiPid = null;

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('fastapi-status', {
          running: false
        });
        mainWindow.webContents.send('fastapi-pid', null);
      }

      return {
        success: true,
        message: `Señal de apagado enviada al servidor (PID: ${pidToLog})`
      };
    } catch (error) {
      console.error('[Electron] Error al apagar FastAPI:', error);

      return {
        success: false,
        message: error.message
      };
    }
  }

  console.log('[Electron] No hay un proceso FastAPI administrado por Electron.');

  return {
    success: false,
    message: 'No hay servidor en ejecución'
  };
}

async function restartFastAPI() {
  const oldPid = fastApiPid;

  console.log(`[Electron] Reiniciando FastAPI. PID anterior: ${oldPid || 'ninguno'}`);

  stopFastAPI();

  // Esperar brevemente a que el puerto quede disponible.
  await new Promise((resolve) => setTimeout(resolve, 1000));

  await startFastAPI();

  return {
    success: true,
    message: `Solicitud de reinicio realizada. PID anterior: ${oldPid || 'N/A'}`
  };
}

function sendPortToRenderer(port) {
  currentPort = port;

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('fastapi-port', port);
    mainWindow.webContents.send('fastapi-status', {
      running: true
    });
    mainWindow.webContents.send('fastapi-pid', fastApiPid);
  }
}

// ---------------------------------------------------------------------------
// Ventana
// ---------------------------------------------------------------------------

function createWindow(port = 8000) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    return;
  }

  mainWindow = new BrowserWindow({
    width: 800,
    height: 800,
    frame: false,
    title: 'Octomation Client',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  const isDev = !app.isPackaged && process.env.NODE_ENV === 'development';
  const distIndex = path.join(__dirname, 'dist-renderer', 'index.html');
  const hasDist = fs.existsSync(distIndex);

  if (isDev && !hasDist) {
    console.log('[Electron] Cargando Vite en http://localhost:5173');

    mainWindow.loadURL('http://localhost:5173').catch((error) => {
      console.error('[Electron] No se pudo cargar Vite:', error);
    });

    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else if (hasDist && (!isDev || process.env.USE_DIST === '1')) {
    mainWindow.loadFile(distIndex);
  } else {
    mainWindow.loadURL('http://localhost:5173').catch((error) => {
      console.error('[Electron] Error cargando Vite:', error);

      if (fs.existsSync(distIndex)) {
        mainWindow.loadFile(distIndex);
      }
    });

    if (!app.isPackaged) {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  }

  mainWindow.webContents.on('did-finish-load', () => {
    if (currentPort) {
      sendPortToRenderer(currentPort);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ---------------------------------------------------------------------------
// Plugins
// ---------------------------------------------------------------------------

function downloadZip(url, dest, pluginName) {
  return new Promise((resolve, reject) => {
    const destinationDir = path.dirname(dest);

    const safePluginName = String(pluginName)
      .trim()
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, '_');

    fs.mkdirSync(destinationDir, { recursive: true });

    const zipPath = path.join(destinationDir, `${safePluginName}.zip`);

    const download = (downloadUrl) => {
      const protocol = downloadUrl.startsWith('https:') ? https : http;

      const request = protocol.get(downloadUrl, {
        headers: {
          'User-Agent': 'Electron-Plugin-Downloader'
        }
      }, (response) => {
        if ([301, 302, 303, 307, 308].includes(response.statusCode)) {
          const location = response.headers.location;
          response.resume();

          if (!location) {
            return reject(new Error('Redirección sin URL de destino'));
          }

          return download(new URL(location, downloadUrl).href);
        }

        if (response.statusCode !== 200) {
          response.resume();
          return reject(
            new Error(`Error al descargar: ${response.statusCode}`)
          );
        }

        const file = fs.createWriteStream(zipPath);

        file.on('error', (error) => {
          request.destroy();
          fs.unlink(zipPath, () => {});
          reject(error);
        });

        response.on('error', (error) => {
          file.destroy();
          fs.unlink(zipPath, () => {});
          reject(error);
        });

        response.pipe(file);

        file.on('finish', () => {
          file.close((error) => {
            if (error) {
              fs.unlink(zipPath, () => {});
              return reject(error);
            }

            resolve(zipPath);
          });
        });
      });

      request.on('error', (error) => {
        fs.unlink(zipPath, () => {});
        reject(error);
      });
    };

    download(url);
  });
}

ipcMain.handle('get-available-plugins', async () => {
  try {
    const data = await new Promise((resolve, reject) => {
      const request = http.get('http://localhost:4005/plugins', (res) => {
        let body = '';

        res.on('data', (chunk) => {
          body += chunk;
        });

        res.on('end', () => {
          if (res.statusCode < 200 || res.statusCode >= 300) {
            return reject(new Error(`Error HTTP: ${res.statusCode}`));
          }

          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(error);
          }
        });
      });

      request.on('error', reject);
      request.setTimeout(10000, () => {
        request.destroy(new Error('Tiempo de espera agotado consultando plugins'));
      });
    });

    return {
      success: true,
      data
    };
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
});

ipcMain.handle('download-plugin', async (_, pluginId) => {
  try {
    const info = await new Promise((resolve, reject) => {
      const request = http.get(
        `http://localhost:4005/plugins/${encodeURIComponent(pluginId)}/download/latest`,
        (res) => {
          let body = '';

          res.on('data', (chunk) => {
            body += chunk;
          });

          res.on('end', () => {
            if (res.statusCode !== 200) {
              return reject(
                new Error(`Error obteniendo el release: ${res.statusCode}`)
              );
            }

            try {
              resolve(JSON.parse(body));
            } catch (error) {
              reject(error);
            }
          });
        }
      );

      request.on('error', reject);
      request.setTimeout(15000, () => {
        request.destroy(new Error('Tiempo de espera agotado obteniendo el release'));
      });
    });

    const zipballUrl = info.zipball_url;

    if (!zipballUrl) {
      throw new Error('No se encontró zipball_url');
    }

    const pluginName = info.pluginName || info.plugin_name;

    if (!pluginName) {
      throw new Error('No se encontró pluginName');
    }

    const pluginNameClean = pluginName
      .toString()
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/-/g, '_')
      .replace(/[<>:"/\\|?*\x00-\x1F]/g, '_');

    const pluginsDir = path.join(getBackendPath(), 'plugins');
    fs.mkdirSync(pluginsDir, { recursive: true });

    const tempDir = app.getPath('temp');
    const zipPath = await downloadZip(
      zipballUrl,
      tempDir,
      pluginNameClean
    );

    const targetPath = path.join(pluginsDir, pluginNameClean);
    const extractTempDir = fs.mkdtempSync(
      path.join(tempDir, 'plugin-extract-')
    );

    try {
      const zip = new AdmZip(zipPath);
      const entries = zip.getEntries();

      const rootEntries = entries
        .filter((entry) => !entry.isDirectory)
        .map((entry) => entry.entryName.replace(/\\/g, '/'))
        .filter((name) => name && !name.startsWith('/'));

      if (rootEntries.length === 0) {
        throw new Error('El ZIP no contiene archivos.');
      }

      const rootDirs = [
        ...new Set(rootEntries.map((name) => name.split('/')[0]))
      ];

      zip.extractAllTo(extractTempDir, true);

      const sourcePath = rootDirs.length === 1
        ? path.join(extractTempDir, rootDirs[0])
        : extractTempDir;

      if (!fs.existsSync(sourcePath)) {
        throw new Error(`No se encontró la carpeta extraída: ${sourcePath}`);
      }

      const stagingPath = path.join(
        pluginsDir,
        `.installing-${pluginNameClean}-${Date.now()}`
      );

      try {
        fs.cpSync(sourcePath, stagingPath, { recursive: true });

        if (fs.existsSync(targetPath)) {
          fs.rmSync(targetPath, { recursive: true, force: true });
        }

        fs.renameSync(stagingPath, targetPath);
      } catch (error) {
        fs.rmSync(stagingPath, { recursive: true, force: true });
        throw error;
      }

      console.log(`[PLUGIN INSTALL] Plugin instalado en: ${targetPath}`);
    } finally {
      try {
        fs.unlinkSync(zipPath);
      } catch (error) {
        console.log('No se pudo eliminar ZIP temporal:', error.message);
      }

      try {
        fs.rmSync(extractTempDir, {
          recursive: true,
          force: true
        });
      } catch (error) {
        console.log('No se pudo limpiar la extracción:', error.message);
      }
    }

    const reqFile = path.join(targetPath, 'requirements.txt');

    if (fs.existsSync(reqFile)) {
      console.log(`[PLUGIN INSTALL] Instalando dependencias desde ${reqFile}`);

      const backendDir = getBackendPath();
      const pythonCommand = await ensureVenv();

      await runCommand(
        pythonCommand,
        ['-m', 'pip', 'install', '-r', reqFile],
        {
          cwd: backendDir,
          env: {
            ...process.env,
            PYTHONUTF8: '1',
            PYTHONIOENCODING: 'utf-8'
          }
        }
      );
    }

    return {
      success: true,
      message: `Plugin ${pluginNameClean} descargado y extraído.`,
      pluginName: pluginNameClean,
      path: targetPath
    };
  } catch (error) {
    console.error('[PLUGIN INSTALL] Error:', error);

    return {
      success: false,
      error: error.message
    };
  }
});

// ---------------------------------------------------------------------------
// IPC y ciclo de vida de la app
// ---------------------------------------------------------------------------

ipcMain.handle('stop-fastapi', stopFastAPI);
ipcMain.handle('restart-fastapi', restartFastAPI);
ipcMain.handle('get-fastapi-port', () => currentPort || 8000);

app.whenReady().then(async () => {
  // Crear la interfaz inmediatamente, aunque FastAPI tarde en arrancar.
  createWindow(8000);

  try {
    const existingPort = await findRunningServer();

    if (existingPort) {
      currentPort = existingPort;
      sendPortToRenderer(existingPort);
      return;
    }

    await startFastAPI();
  } catch (error) {
    console.error('[Electron] Error iniciando la aplicación:', error);

    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('fastapi-status', {
        running: false,
        error: error.message
      });
    }
  }
}).catch((error) => {
  console.error('[Electron] Error crítico:', error);
});

app.on('window-all-closed', () => {
  console.log('[Electron] Ventanas cerradas. FastAPI permanece activo mientras Electron siga abierto.');
});

app.on('before-quit', () => {
  console.log('[Electron] Saliendo de Octomation Client.');

  // Cerrar el proceso que este cliente inició.
  // No intenta detener un servidor ajeno que ya estuviera ejecutándose.
  if (fastApiProcess && !fastApiProcess.killed) {
    fastApiProcess.kill();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow(currentPort || 8000);

    if (!fastApiProcess) {
      startFastAPI().catch((error) => {
        console.error('[Electron] Error al reactivar FastAPI:', error);
      });
    }
  }
});
