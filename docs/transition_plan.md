# mLRS Flasher Electron Transition Plan

This document outlines the remaining steps to fully transition the mLRS Flasher application from the legacy Python/CustomTkinter implementation to the new Electron/React framework.

## 1. Implementation Gaps & Enhancements

### App Update Notifications
**Status**: Missing
**Description**: The current application does not notify the user when a new version of the mLRS Flasher application itself is available.
**Action Items**:
- [ ] Implement a check against GitHub Releases (e.g., `olliw42/mLRS-Flasher-Electron` or similar repo) on startup.
- [ ] Display a notification in the UI if a new version is available.
- [ ] (Optional) Integrate `electron-updater` for auto-updates.

### Console Log Export
**Status**: Missing
**Description**: Users need a way to easily share logs for troubleshooting.
**Action Items**:
- [ ] Implement a "Save Logs" button in the Console component.
- [ ] Add functionality to export the current console buffer to a `.txt` file using Electron's `showSaveDialog`.

## 2. Cleanup & Project Structure

### Legacy Removal
**Status**: Pending
**Description**: Remove files associated with the legacy Python application to avoid confusion.
**Action Items**:
- [ ] **Root Config & Scripts**:
    - Delete `mLRS_Flasher.ini` (Legacy settings).
    - Delete `mLRS_Flasher.py` (Legacy application).
    - Delete `run_mLRS_Flasher_mac.sh` (Legacy launcher).
- [ ] **Directories**:
    - Delete `tools/` directory (Contains legacy PyInstaller specs).
- [ ] **Scripts Folder**:
    - Delete `scripts/mLRS_Flasher_cli.py.bak`.

### Root Structure Consolidation
**Status**: Planned
**Description**: Move `electron/*` contents to the project root to simplify development and build pipelines.
**Action Items**:
- [ ] Merge `electron/package.json` with the root `package.json`.
- [ ] Move `src/`, `public/`, and config files to the root.
- [ ] Update build scripts and path references in `main.cjs` and `preload.cjs`.

## 3. Documentation & Build Config

**Status**: Pending
**Description**: Update documentation and build processes for the new architecture.
**Action Items**:
- [ ] **README.md**:
    - Detail development workflow (`npm run dev`).
    - Detail production build commands (`npm run build:win/mac/linux`).
    - Explain the bundled Python runtime and dependency management.
    - **Add Notes**:
        - Document how to remove the macOS quarantine attribute (`xattr -d com.apple.quarantine`) for unsigned distributions.
        - **Linux Packaging**: Add `.deb` and `.rpm` targets to `electron-builder` config to handle `libfuse2` and other dependencies automatically via the system package manager.
- [ ] **CI/CD**:
    - Update GitHub Actions to automate Electron builds and releases (including `.exe`, `.dmg`, `.AppImage`, and `.deb`).

## 4. Testing & Verification

**Status**: In Progress
**Description**: Ensure the new application works consistently across platforms.
**Action Items**:
- [ ] **Cross-Platform Verification**:
    - **Windows**: Verify embedded Python path resolution.
    - **Linux**: Verify AppImage build.
    - **macOS**: Verify DMG build and basic functionality.
- [ ] **Functionality**:
    - Verify Passthrough modes (AP Passthru, EdgeTX Passthru).
    - Verify proper handling of "No DTR" and other special flag logic for ESP devices.
- [ ] **Update Verification**:
    - Verify the update notification system once implemented.
