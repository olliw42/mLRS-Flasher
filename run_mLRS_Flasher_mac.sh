#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print a status message
function status() {
    echo -e "\033[1;32m$1\033[0m"
}

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    status "🔧 Installing Homebrew."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for this script (Apple Silicon vs Intel paths)
    if [[ -d /opt/homebrew/bin ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    status "✅ Homebrew installed."
else
    status "✅ Homebrew already installed."
fi

# Ensure brew is in PATH now
if ! command -v brew &> /dev/null; then
    echo "Error: brew not found in PATH even after install."
    exit 1
fi

# Install Python if not present
if ! command -v python3 &> /dev/null; then
    status "🔧 Installing Python via Homebrew."
    brew install python
    status "✅ Python3 installed."
else
    status "✅ Python3 already installed."
fi

# Install virtualenv if not present
if ! command -v virtualenv &> /dev/null; then
    status "🔧 Installing virtualenv."
    brew install virtualenv
    status "✅ Virtualenv installed."
else
    status "✅ Virtualenv already installed."
fi

# Add Homebrew Python to PATH in ~/.zprofile if not already present
add_python_to_path() {
    local zprofile="$HOME/.zprofile"
    local path_line='export PATH="$(brew --prefix python)/libexec/bin:$PATH"'

    if ! grep -Fxq "$path_line" "$zprofile" 2>/dev/null; then
        echo "" >> "$zprofile"
        echo "# Add Homebrew Python to PATH" >> "$zprofile"
        echo "$path_line" >> "$zprofile"
        status "✅ Added Homebrew Python to PATH in ~/.zprofile"
    else
        status "✅ Python path already in ~/.zprofile"
    fi
}

# Remove quarantine attributes from all files in current directory
remove_quarantine_attribute() {
    local dir="$1"
    status "🔧 Removing quarantine attributes."
    find "$dir" -print0 | while IFS= read -r -d '' file; do
        xattr -d com.apple.quarantine "$file" 2>/dev/null || true
    done
    status "✅ Quarantine attributes removed."
}

# Set up a virtual environment and install dependencies
setup_virtualenv() {
    status "🔧 Creating virtual environment."
    virtualenv --python="$(which python)" venv

    status "🔧 Upgrading pip."
    ./venv/bin/python -m pip install --upgrade pip

    status "🔧 Installing Python packages."
    ./venv/bin/pip install pillow requests pyserial customtkinter tk

    status "🔧 Installing python-tk via Homebrew (if needed)."
    brew install python-tk || true
}

# Run the Python script inside the venv
run_flasher() {
    status "🚀 Running mLRS_Flasher.py."
    source ./venv/bin/activate
    ./mLRS_Flasher.py
}

### MAIN ###
if [ -d "venv" ]; then
    status "✅ Virtual environment already exists. Launching flasher."
    run_flasher
else
    status "🔧 Virtual environment not found. Preparing environment."
    add_python_to_path
    remove_quarantine_attribute "$(pwd)"
    setup_virtualenv
    status "✅ Virtual environment created."
    run_flasher
fi
