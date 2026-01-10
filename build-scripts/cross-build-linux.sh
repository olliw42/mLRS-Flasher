#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "============================================"
echo "  mLRS Flasher - Cross-Build for Linux x64 (from macOS)"
echo "============================================"
echo

# Platform paths
PLATFORM_DIR="python/linux"
TARGET_PYTHON_DIR="$PLATFORM_DIR/python"
TARGET_SITE_PACKAGES="$TARGET_PYTHON_DIR/lib/python3.12/site-packages"
HOST_PYTHON="python/macos/python/bin/python3"

# 1. Setup Python for Linux
echo "[1/3] Setting up Linux Python Runtime..."
PYTHON_INSTALLED_MARKER="$PLATFORM_DIR/.installed"

if [ -f "$PYTHON_INSTALLED_MARKER" ]; then
    echo "      Linux Python runtime and dependencies valid (marker found). Skipping setup."
else
    echo "      Runtime not found or incomplete. Starting fresh setup..."
    
    # Check/Download Python
    if [ ! -d "$TARGET_PYTHON_DIR" ]; then
        echo "      Downloading Linux Python..."
        node scripts/download-python.js linux
    else
        echo "      Linux Python found."
    fi

    # 2. Install Dependencies (Using Host Python, Targeting Linux Libs)
    echo "      Installing Python dependencies (Cross-Targeting Linux)..."
    # Ensure Host Python exists
    if [ ! -f "$HOST_PYTHON" ]; then
        echo "      Host Python ($HOST_PYTHON) not found. Attempting to use system python3..."
        HOST_PYTHON="python3"
    fi

    # Create site-packages if strictly missing
    mkdir -p "$TARGET_SITE_PACKAGES"

    # Install deps
    echo "      Installing requests, pyserial, pymavlink, future, lxml, bitstring, ecdsa, reedsolo, cryptography..."
    "$HOST_PYTHON" -m pip install \
        --platform manylinux2014_x86_64 \
        --only-binary=:all: \
        --target "$TARGET_SITE_PACKAGES" \
        --upgrade \
        requests pyserial pymavlink future lxml bitstring ecdsa reedsolo cryptography

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install Python modules."
        exit 1
    fi

    # 3. Optimize Python (Removes bloat and Pillow if present)
    echo "      Optimizing Linux Python runtime..."
    "$HOST_PYTHON" scripts/optimize_python.py "$PLATFORM_DIR"
    
    touch "$PYTHON_INSTALLED_MARKER"
    echo "      Linux Python setup complete."
fi

echo

# 4. Build Electron App
echo "[3/3] Building Electron AppImage (x64)..."
cd electron

if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    echo "      Dependencies outdated or missing. Running 'npm install'..."
    npm install
    if [ $? -ne 0 ]; then
        echo "ERROR: npm install failed."
        exit 1
    fi
    # Touch node_modules to update its timestamp to now, preventing re-run next time
    touch node_modules
else
    echo "      Dependencies appear up to date. Skipping 'npm install'."
fi
# Run vite build first
npm run build
# Explicitly build for Linux x64
npx electron-builder --linux --x64

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed."
    exit 1
fi

cd ..
echo
echo "============================================"
echo "  Linux x64 Build Complete!"
echo "  Output: dist/"
echo "============================================"
ls -l dist/*.AppImage 2>/dev/null
