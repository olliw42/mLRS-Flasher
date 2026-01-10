# Version Update Guide

This document outlines the steps required to update the version number of the mLRS Flasher application. To ensure consistency across the UI, build system, and metadata, please update the version in the following files.

> [!IMPORTANT]
> Do NOT update the version string or date headers in `mLRS_Flasher.py`. This file is part of the legacy implementation and its versioning is managed separately.

## 1. Root Package Configuration
Update the version string in the root `package.json`. This is used for general project tracking and script execution.

- **File**: `/package.json`
- **Field**: `"version"`

```json
{
  "name": "mlrs-flasher",
  "version": "0.2.0",
  ...
}
```

## 2. Electron Package Configuration
Update the version string in the Electron-specific `package.json`. This version is used by `electron-builder` to set the version of the generated executables (`.exe`, `.dmg`, `.AppImage`).

- **File**: `/electron/package.json`
- **Field**: `"version"`

```json
{
  "name": "mlrs-flasher-electron",
  "version": "0.2.0",
  ...
}
```

## 3. UI Navigation Footer
Update the version displayed in the application's sidebar/navigation footer.

- **File**: `/electron/src/components/Navigation.jsx`
- **Location**: Near the bottom of the component, inside the `nav-footer` div.

```jsx
<div className="nav-footer">
  <span className="version">v0.2.0</span>
</div>
```

## 4. Main Process Metadata
Update the date comment in the Electron main process file to reflect the last modification.

- **File**: `/electron/main.cjs`
- **Location**: Line 2 (comment header).

```javascript
const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
// 2026-01-10
```

## 5. Synchronization
After updating the `package.json` files, it is recommended to run `npm install` (or `npm install` inside the `electron` folder) to ensure `package-lock.json` is synchronized.

---
*Last Updated: 2026-01-10*
