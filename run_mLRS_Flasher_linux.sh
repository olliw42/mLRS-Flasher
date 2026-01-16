#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Function to print a status message
function status() {
    echo -e "\033[1;32m$1\033[0m"
}

# Set up a virtual environment and install dependencies
setup_virtualenv() {
    status "🔧 Creating virtual environment."
    virtualenv venv

    source venv/bin/activate

    status "🔧 Upgrading pip."
    pip install --upgrade pip

    status "🔧 Installing Python packages."
    pip install lxml pillow requests pyserial customtkinter tk
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
    setup_virtualenv
    status "✅ Virtual environment created."
    run_flasher
fi


