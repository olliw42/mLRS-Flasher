#!/usr/bin/env python
#*******************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
#*******************************************************
# Win Launcher
#********************************************************

import subprocess
import os

def setup_virtualenv():
    """Creates and sets up a virtual environment using venv."""
    # Create virtual environment
    subprocess.run(["python", "-m", "venv", "venv"], check=True)
    print("Virtual environment created.")
    
    # Upgrade pip
    subprocess.run(["venv\\Scripts\\python", "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print("Pip upgraded.")
    
    # Install required modules
    subprocess.run(["venv\\Scripts\\python", "-m", "pip", "install", "pillow", "requests", "pyserial", "customtkinter", "tk"], check=True)
    print("Required modules installed.")

def run_flasher():
    """Runs the mLRS_Flasher.py script within the virtual environment."""
    subprocess.run(["venv\\Scripts\\python", "mLRS_Flasher.py"], check=True)
    print("mLRS_Flasher.py executed successfully.")

if __name__ == "__main__":
    # Check if venv folder exists before running run_flasher
    if os.path.isdir("venv"):
        print("Virtual environment found, running flasher script...")
        run_flasher()
    else:
        print("Virtual environment not found. Setting up virtual environment...")
        setup_virtualenv()
        run_flasher()
