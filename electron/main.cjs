const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
// 2026-01-11
const { spawn } = require('child_process');
const path = require('path');

// determine if we're in development or production
const isDev = !app.isPackaged;

// resolve embedded python path based on platform
function getPythonPath() {
  const platform = process.platform === 'win32' ? 'windows' :
    process.platform === 'darwin' ? 'macos' : 'linux';

  const basePath = isDev
    ? path.join(__dirname, '..', 'python', platform)
    : path.join(process.resourcesPath, 'python');

  if (process.platform === 'win32') {
    // windows embed zip extracts flat
    return path.join(basePath, 'python.exe');
  }
  // macos/linux python-build-standalone extracts with nested python/ folder
  return path.join(basePath, 'python', 'bin', 'python3');
}

// resolve script path
function getScriptPath(script) {
  const basePath = isDev
    ? path.join(__dirname, '..', 'scripts')
    : path.join(process.resourcesPath, 'scripts');
  return path.join(basePath, script);
}

// resolve thirdparty path (for PYTHONPATH)
function getThirdpartyPath() {
  return isDev
    ? path.join(__dirname, '..', 'thirdparty')
    : path.join(process.resourcesPath, 'thirdparty');
}

// generic python command runner with streaming output
function runPythonCommand(scriptName, args, event) {
  const pythonPath = getPythonPath();
  const scriptPath = getScriptPath(scriptName);

  // set up environment with thirdparty and scripts in PYTHONPATH
  const env = {
    ...process.env,
    PYTHONPATH: `${getThirdpartyPath()}${path.delimiter}${getScriptPath('')}`
  };

  console.log(`[Python] Running: ${pythonPath} ${scriptPath} ${args.join(' ')}`);

  const proc = spawn(pythonPath, ['-u', scriptPath, '--json', ...args], { env });
  currentProc = proc;

  let stdoutRemainder = '';
  proc.stdout.on('data', (data) => {
    stdoutRemainder += data.toString();
    const parts = stdoutRemainder.split(/\r\n|\r|\n/);
    stdoutRemainder = parts.pop(); // keep partial line for next chunk

    parts.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) return;

      console.log(`[Python stdout] ${trimmed}`); // visibility in terminal

      try {
        const parsed = JSON.parse(trimmed);
        event.sender.send('python-output', parsed);
      } catch {
        // not JSON, send as log message
        event.sender.send('python-output', { type: 'log', message: trimmed });
      }
    });
  });

  proc.stderr.on('data', (data) => {
    const message = data.toString();
    console.error('[Python stderr]', message);
    event.sender.send('python-output', { type: 'stderr', message });
  });

  proc.on('close', (code) => {
    console.log(`[Python] Process exited with code ${code}`);
    event.sender.send('python-complete', { code });
    if (currentProc === proc) currentProc = null;
  });

  proc.on('error', (err) => {
    console.error('[Python] Failed to start:', err);
    event.sender.send('python-output', { type: 'error', message: err.message });
    event.sender.send('python-complete', { code: -1 });
  });

  return proc;
}

// run python command and return promise with result
function runPythonCommandAsync(scriptName, args) {
  return new Promise((resolve, reject) => {
    const pythonPath = getPythonPath();
    const scriptPath = getScriptPath(scriptName);

    const env = {
      ...process.env,
      PYTHONPATH: `${getThirdpartyPath()}${path.delimiter}${getScriptPath('')}`
    };

    console.log(`[Python Async] Running: ${pythonPath} ${scriptPath} ${args.join(' ')}`);

    const proc = spawn(pythonPath, ['-u', scriptPath, '--json', ...args], { env });
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data; });
    proc.stderr.on('data', (data) => { stderr += data; });

    proc.on('close', (code) => {
      if (code === 0) {
        // python outputs multiple JSON lines - log messages and the actual result
        // the result is the last non-empty line that contains the data we need
        const lines = stdout.split('\n').filter(l => l.trim());
        for (let i = lines.length - 1; i >= 0; i--) {
          try {
            const parsed = JSON.parse(lines[i]);
            // skip log messages, look for the actual result object
            if (!parsed.type || (parsed.type !== 'log' && parsed.type !== 'info' && parsed.type !== 'error')) {
              resolve(parsed);
              return;
            }
          } catch {
            // not valid JSON, continue
          }
        }
        // if no valid result found, return empty object
        resolve({});
      } else {
        console.error(`[Python Async Search] Error: ${stderr}`);
        const error = new Error(`Python exited with code ${code}: ${stderr}`);
        error.stderr = stderr;
        error.stdout = stdout;
        reject(error);
      }
    });

    proc.on('error', reject);
  });
}

// main window and process references
let mainWindow;
let currentProc = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    show: false,  // don't show until maximized
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    },
    icon: isDev
      ? path.join(__dirname, '..', 'assets', process.platform === 'win32' ? 'mLRS_logo_round.ico' : 'mLRS_logo_512.png')
      : path.join(process.resourcesPath, 'assets', process.platform === 'win32' ? 'mLRS_logo_round.ico' : 'mLRS_logo_512.png')
  });

  // load vite dev server in dev, built files in production
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  // maximize and show window after content loads
  mainWindow.once('ready-to-show', () => {
    mainWindow.maximize();
    mainWindow.show();
  });
}

// IPC handlers

ipcMain.handle('pick-directory', async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const result = await dialog.showOpenDialog(win, {
    properties: ['openDirectory', 'createDirectory'],
    title: 'Select Download Location for Lua Scripts',
    buttonLabel: 'Select Folder'
  });
  if (result.canceled) {
    return null;
  }
  return result.filePaths[0];
});

ipcMain.handle('list-versions', async () => {
  return runPythonCommandAsync('mLRS_Flasher_cli.py', ['list-versions']);
});

ipcMain.handle('list-devices', async (event, type) => {
  return runPythonCommandAsync('mLRS_Flasher_cli.py', ['list-devices', '--type', type]);
});

ipcMain.handle('list-firmware', async (event, options) => {
  const args = ['list-firmware', '--type', options.type, '--version', options.version];
  if (options.device) {
    args.push('--device', options.device);
  }
  return runPythonCommandAsync('mLRS_Flasher_cli.py', args);
});

ipcMain.handle('list-ports', async () => {
  return runPythonCommandAsync('mLRS_Flasher_cli.py', ['list-ports']);
});

ipcMain.handle('get-metadata', async (event, options) => {
  return runPythonCommandAsync('mLRS_Flasher_cli.py', [
    'get-metadata',
    '--type', options.type,
    '--device', options.device,
    '--filename', options.filename
  ]);
});

// flash command streams output, doesn't return a single result
ipcMain.on('flash', (event, options) => {
  const args = [
    'flash',
    '--type', options.type,
    // programmer is now optional/fallback, but we still pass it if present
    '--programmer', options.programmer || 'auto',
    '--url', options.url,
    '--filename', options.filename
  ];

  if (options.device) {
    args.push('--device', options.device);
  }
  if (options.flashMethod) {
    args.push('--flash-method', options.flashMethod);
  }
  if (options.port) {
    args.push('--port', options.port);
  }
  if (options.baudrate) {
    args.push('--baudrate', options.baudrate.toString());
  }
  runPythonCommand('mLRS_Flasher_cli.py', args, event);
});

ipcMain.on('download-lua', (event, options) => {
  const args = [
    'download-lua',
    '--version', options.version,
    '--output', options.output
  ];
  if (options.filename) {
    args.push('--filename', options.filename);
  }
  runPythonCommand('mLRS_Flasher_cli.py', args, event);
});

ipcMain.on('cancel-python', () => {
  if (currentProc) {
    console.log('[Electron] Cancelling Python process...');
    currentProc.kill();
    currentProc = null;
  }
});

// app lifecycle
app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
