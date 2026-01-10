# Building mLRS Flasher

This document covers building the Electron app for macOS, Windows, and Linux.

## Prerequisites

### All Platforms
- Node.js 18+ and npm
- Python 3.9+ (for downloading embedded runtimes)

### Platform-Specific Python Runtimes
Before building, you need to download the embedded Python runtime for each target platform. These are placed in `python/<platform>/`.

```bash
# download python runtimes (run from project root)
node scripts/download-python.js macos   # for macOS builds
node scripts/download-python.js windows # for Windows builds
node scripts/download-python.js linux   # for Linux builds
# or download all
node scripts/download-python.js all
```

### Installing Python Modules
The embedded Python runtimes need the `requests` and `pyserial` modules installed. After downloading the runtime, install them:

**Windows:**
```powershell
cd python/windows
Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
.\python.exe get-pip.py --no-warn-script-location
.\python.exe -m pip install requests pyserial --no-warn-script-location
Remove-Item get-pip.py
```

**macOS:**
```bash
cd python/macos/python
./bin/python3 -m pip install requests pyserial
```

**Linux:**
```bash
cd python/linux/python
./bin/python3 -m pip install requests pyserial
```

### Optimizing Python Runtime (Recommended)
To significantly reduce the build size (e.g. from ~190MB to ~150MB), run the optimization script to prune unused files and dialects.

**Windows:**
```powershell
.\python\windows\python.exe scripts/optimize_python.py python/windows
```

**macOS:**
```bash
python/macos/python/bin/python3 scripts/optimize_python.py python/macos
```

**Linux:**
```bash
python/linux/python/bin/python3 scripts/optimize_python.py python/linux
```

> [!TIP]
> Use the automated build scripts in `build-scripts/` to handle downloading, installing, and optimizing automatically.


## Development

```bash
cd electron
npm install
npm run dev
```

## Production Builds

### macOS (.dmg)
```bash
cd electron
npm run build:mac
```
Output: `dist/mLRS Flasher-<version>.dmg`

*Alternatively, run `build-scripts/build-mac.sh` to automate the entire process.*

### Windows (.exe installer)
```bash
cd electron
npm run build:win
```
Output: `dist/mLRS Flasher Setup <version>.exe`

> [!NOTE]
> Cross-compiling Windows from macOS requires Wine. Native Windows builds are recommended.

### Linux (.AppImage)
```bash
cd electron
npm run build:linux
```
Output: `dist/mLRS Flasher-<version>.AppImage`

## Build Output

All build artifacts are placed in the `electron/dist/` folder.

## Bundled Resources

The following are bundled with each build:
- `scripts/` - Python CLI scripts
- `thirdparty/` - Python dependencies (intelhex, pyserial, etc.)
- `python/` - Platform-specific embedded Python runtime
- `assets/` - Icons and images

## Troubleshooting

### macOS code signing
For distribution, you'll need an Apple Developer account. For local testing, the unsigned app works but may require allowing it in System Preferences > Security.

### Linux permissions
AppImage files need to be made executable:
```bash
chmod +x "mLRS Flasher-<version>.AppImage"
```

#### Running on newer distributions (Ubuntu 22.04+)
If the app fails to open, you may need to install the FUSE 2 library:
```bash
sudo apt install libfuse2
```

Alternatively, you can extract the AppImage and run it without FUSE:
```bash
./"mLRS Flasher-<version>.AppImage" --appimage-extract
./squashfs-root/AppRun
```

### Windows symlink permission error
When building on Windows, electron-builder downloads a code signing utility that contains macOS symlinks. Extracting these symlinks may fail with:
```
ERROR: Cannot create symbolic link : A required privilege is not held by the client.
```

**Solution 1: Enable Developer Mode** (recommended)
Go to Settings > Update & Security > For developers and enable "Developer Mode". This allows symlink creation without admin rights.

**Solution 2: Manual cache fix**
If Developer Mode isn't available, you can manually fix the cache after the first failed attempt:
```powershell
# the extraction actually succeeds for Windows files; rename the folder to bypass the error
$cache = "$env:LOCALAPPDATA\electron-builder\Cache\winCodeSign"
Remove-Item "$cache\*.7z" -Force -ErrorAction SilentlyContinue
$latest = Get-ChildItem $cache -Directory | Sort-Object LastWriteTime -Desc | Select-Object -First 1
Rename-Item $latest.FullName -NewName "winCodeSign-2.6.0"
# then re-run: npm run build:win
```

### Windows SmartScreen
Unsigned Windows builds will trigger SmartScreen warnings. Users can click "More info" > "Run anyway" to proceed.
