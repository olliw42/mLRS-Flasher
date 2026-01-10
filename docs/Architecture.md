# mLRS Flasher Architecture

The mLRS Flasher is a hybrid desktop application that combines a modern web-based UI (Electron) with a robust Python backend for hardware interaction.

## High-Level Overview

The application is structured into three main layers:

1.  **Renderer Process (UI):** Built with React and Vite. It handles user interaction, state management, and visualization.
2.  **Main Process (Electron):** Manages the application lifecycle, window creation, and acts as a secure bridge between the UI and the system.
3.  **Python Backend:** A standalone Python environment that executes the actual flashing logic, serial port management, and hardware communication.

## Detailed Component Breakdown

### 1. Renderer Process (UI)
*   **Location:** `electron/src/`
*   **Tech Stack:** React, Vite.
*   **Responsibility:** 
    *   Displays the user interface.
    *   Sends user actions (e.g., "Flash Firmware") to the Main process via IPC.
    *   Listens for progress updates and logs via IPC.
*   **Security:** Uses a `preload.js` script to expose a limited, safe API (`window.api`) via `contextBridge`. No direct Node.js access is allowed in the renderer.

### 2. Main Process (Electron)
*   **Location:** `electron/main.js`
*   **Responsibility:**
    *   **Orchestration:** Starts the application and creates the browser window.
    *   **Python Management:** Spawns the Python subprocess using `child_process.spawn`. It manages the pathing for both Development (local python) and Production (bundled standalone python).
    *   **IPC Handling:** receives commands like `list-devices`, `flash`, or `download-lua`.
    *   **Streaming:** Reads `stdout` and `stderr` from the Python process, parses line-delimited JSON messages, and streams them back to the UI.

### 3. Python Backend
*   **Location:** `scripts/` and `mLRS_Flasher.py`
*   **Entry Point:** `scripts/mLRS_Flasher_cli.py`
*   **Mechanism:**
    *   The Electron Main process calls the CLI script with specific arguments (e.g., `--flash-method`).
    *   **JSON Communication:** The Python script outputs status, logs, and data as JSON objects on `stdout`.
    *   **Legacy Logic:** It imports and reuses the core logic from the original `mLRS_Flasher.py` (which was a Tkinter app), ensuring consistent behavior with the legacy tool.
    *   **Dependencies:** Runs in a self-contained Python environment (downloaded during build) involving `pyserial`, `requests`, `esptool`, etc.

## Data Flow: The Flashing Process

1.  **User Action:** User clicks "Flash" in the UI.
2.  **IPC Call:** Renderer calls `window.api.flash(options)`.
3.  **Process Spawn:** Main process spawns `python mLRS_Flasher_cli.py flash ...`.
4.  **Execution:** 
    *   Python parses arguments.
    *   Downloads firmware if a URL is provided.
    *   Identifies the correct external tool (`esptool` or `STM32CubeProgrammer`).
    *   Executes the flashing tool as a subprocess.
5.  **Feedback Loop:**
    *   Python captures output from the flashing tool.
    *   Python converts output to JSON progress messages (e.g., `{"type": "progress", "percent": 45}`).
    *   Electron Main reads these JSON lines and forwards them to the Renderer via `ipcRenderer.send('python-output', ...)`.
    *   UI updates the progress bar.

## Build System

*   **Electron Builder:** Packages the Electron app.
*   **Python Bundling:**
    *   Scripts in `package.json` (`install:python`, `install:deps:*`) download a standalone Python build for the target OS (Mac/Win/Linux).
    *   This standalone Python folder is copied into the application resources (`dist/` or `Resources/`) during the build.
    *   This ensures the end-user does not need Python installed on their machine.
