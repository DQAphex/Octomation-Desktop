const { contextBridge, ipcRenderer, safeStorage } = require('electron');

contextBridge.exposeInMainWorld('api', {
  version: () => process.versions.electron,
  stopFastAPI: () => ipcRenderer.invoke('stop-fastapi'),
  restartFastAPI: () => ipcRenderer.invoke('restart-fastapi'),
  getFastApiPort: () => ipcRenderer.invoke('get-fastapi-port'),
  getAvailablePlugins: () => ipcRenderer.invoke('get-available-plugins'),
  downloadPlugin: (pluginId) => ipcRenderer.invoke('download-plugin', pluginId),
  onPortUpdate: (callback) => {
    ipcRenderer.removeAllListeners('fastapi-port');
    ipcRenderer.on('fastapi-port', (_event, port) => callback(port));
  },
  onStatusUpdate: (callback) => {
    ipcRenderer.removeAllListeners('fastapi-status');
    ipcRenderer.on('fastapi-status', (_event, status) => callback(status));
  },
  onPidUpdate: (callback) => {
    ipcRenderer.removeAllListeners('fastapi-pid');
    ipcRenderer.on('fastapi-pid', (_event, pid) => callback(pid));
  },
  minimize: () => ipcRenderer.send('window:minimize'),
  maximize: () => ipcRenderer.send('window:maximize'),
  close: () => ipcRenderer.send('window:close'),
  auth: {
    isEncryptionAvailable: () => safeStorage.isEncryptionAvailable(),
    encrypt: (text) => {
      if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('safeStorage no disponible');
      }
      const buffer = safeStorage.encryptString(String(text));
      return buffer.toString('base64');
    },
    decrypt: (base64) => {
      if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('safeStorage no disponible');
      }
      const buffer = Buffer.from(String(base64), 'base64');
      return safeStorage.decryptString(buffer);
    }
  }
});
