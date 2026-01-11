#!/bin/bash

# build-linux.sh
# Automated build script for mLRS Flasher (Linux)
# Updated: 2026-01-09

set -e

echo
echo "============================================"
echo "  mLRS Flasher - Build Script (Linux)"
echo "============================================"
echo

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+ and try again."
    exit 1
fi

PLATFORM="linux"
PYTHON_BIN="python/linux/python/bin/python3"
NPM_BUILD_CMD="npm run build:linux"

# Navigate to project root
cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

# Cleanup previous builds
echo "Cleaning up dist/ directory..."
rm -rf dist
echo

# Step 1: Download Python Runtime
echo "[1/4] Checking Python runtime for $PLATFORM..."

PYTHON_INSTALLED_MARKER="python/$PLATFORM/.installed"

if [ -f "$PYTHON_INSTALLED_MARKER" ]; then
    echo "      Python runtime valid (marker found). Skipping download/install."
    echo
    echo "[2/4] Installing Python modules..."
    echo "      Skipping (bundled with runtime)."
else
    echo "      Runtime not found or incomplete. Starting fresh install..."
    
    # Cleanup potential partial installs
    rm -rf "python/$PLATFORM"

    echo "      Running scripts/download-python.js..."
    node scripts/download-python.js "$PLATFORM"
    
    if [ ! -f "$PYTHON_BIN" ]; then
        echo "ERROR: Python binary not found at $PYTHON_BIN after download step."
        exit 1
    fi
     
    # Check again if pip needs to be installed via get-pip
    if ! "$PYTHON_BIN" -m pip --version &> /dev/null; then
         echo "      pip not found. Downloading get-pip.py..."
         curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
         "$PYTHON_BIN" get-pip.py
         rm get-pip.py
    fi

    # Step 2: Install Python modules
    echo "[2/4] Installing Python modules..."
    echo "      Installing requests and pyserial..."
    "$PYTHON_BIN" -m pip install requests pyserial pymavlink future lxml bitstring ecdsa reedsolo cryptography
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install Python modules."
        exit 1
    fi

    echo "      Optimizing Python runtime..."
    "$PYTHON_BIN" scripts/optimize_python.py "python/$PLATFORM"
    
    # Create marker file
    touch "$PYTHON_INSTALLED_MARKER"
    echo "      Python setup complete."
fi

echo "[2.5/4] Setting permissions..."
# Ensure Python binary and libs are executable
# (Recursively set +x on bin/ directory to catch python3, pip, etc.)
if [ -d "python/$PLATFORM/python/bin" ]; then
    echo "      Setting +x on Python binaries..."
    chmod -R +x "python/$PLATFORM/python/bin"
fi

# Ensure STM32CubeProgrammer binary is executable
if [ -f "thirdparty/STM32CubeProgrammer/linux/bin/STM32_Programmer_CLI" ]; then
    echo "      Setting +x on STM32_Programmer_CLI..."
    chmod +x "thirdparty/STM32CubeProgrammer/linux/bin/STM32_Programmer_CLI"
fi

echo

# Step 3: Install npm dependencies
echo "[3/4] Installing npm dependencies..."
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
echo

# Step 4: Build executable
echo "[4/4] Building executable..."
$NPM_BUILD_CMD
if [ $? -ne 0 ]; then
    echo "ERROR: Build failed."
    exit 1
fi

cd ..
echo
echo "============================================"
echo "  Build Complete!"
echo "============================================"
echo
echo "Output located in: dist/"
echo
ls -1 dist/*.AppImage 2>/dev/null || true
