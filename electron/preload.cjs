const { contextBridge, ipcRenderer } = require('electron');
// 2026-01-09

// expose safe API to renderer process
contextBridge.exposeInMainWorld('api', {
  // async queries that return data
  listVersions: () => ipcRenderer.invoke('list-versions'),
  listDevices: (type) => ipcRenderer.invoke('list-devices', type),
  listFirmware: (options) => ipcRenderer.invoke('list-firmware', options),
  listPorts: () => ipcRenderer.invoke('list-ports'),
  getMetadata: (options) => ipcRenderer.invoke('get-metadata', options),
  pickDirectory: () => ipcRenderer.invoke('pick-directory'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  
  // streaming commands
  flash: (options) => ipcRenderer.send('flash', options),
  downloadLua: (options) => ipcRenderer.send('download-lua', options),
  cancelPython: () => ipcRenderer.send('cancel-python'),
  
  // event listeners for streaming output
  onOutput: (callback) => {
    const handler = (_, data) => callback(data);
    ipcRenderer.on('python-output', handler);
    return () => ipcRenderer.removeListener('python-output', handler);
  },
  onComplete: (callback) => {
    const handler = (_, data) => callback(data);
    ipcRenderer.on('python-complete', handler);
    return () => ipcRenderer.removeListener('python-complete', handler);
  },
});
