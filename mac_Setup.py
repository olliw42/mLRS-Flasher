import os
import subprocess

def remove_quarantine_attribute(directory):
    """Recursively removes the quarantine attribute from all files in the given directory."""
    for root, dirs, files in os.walk(directory):
        for name in dirs + files:
            file_path = os.path.join(root, name)
            try:
                subprocess.run(["xattr", "-d", "com.apple.quarantine", file_path], check=True, stderr=subprocess.DEVNULL)
                print(f"Removed quarantine from: {file_path}")
            except subprocess.CalledProcessError:
                print(f"Failed to remove quarantine from: {file_path}")

def setup_virtualenv():
    """Creates and sets up a virtual environment using virtualenv."""
    subprocess.run(["virtualenv", "--python=/opt/homebrew/bin/python3", "venv"], check=True)
    print("Virtual environment created using Homebrew's Python.")
    
    subprocess.run(["venv/bin/python", "-m", "pip", "install", "--upgrade", "pip"], check=True)
    print("Pip upgraded.")
    
    subprocess.run(["venv/bin/python", "-m", "pip", "install", "pillow", "requests", "pyserial", "customtkinter", "tk"], check=True)
    print("Required modules installed including Tkinter in virtual environment.")
    
    subprocess.run(["brew", "install", "python-tk"], check=True)
    print("python-tk installed via Homebrew.")

def run_flasher():
    """Runs the mLRS_Flasher.py script within the virtual environment."""
    subprocess.run(["venv/bin/python", "mLRS_Flasher.py"], check=True)
    print("mLRS_Flasher.py executed successfully within the virtual environment.")

if __name__ == "__main__":
    current_directory = os.getcwd()
    remove_quarantine_attribute(current_directory)
    setup_virtualenv()
    run_flasher()
