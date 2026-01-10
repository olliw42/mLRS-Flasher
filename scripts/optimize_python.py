#!/usr/bin/env python3
import os
import shutil
import sys
import glob

# Constants for cleanup
PATHS_TO_PRUNE = [
    # Mac/Linux paths usually inside 'python/' subdir for standalone builds
    'python/include', 
    'python/share',
    'python/bin/__pycache__',
    # Windows paths
    'include',
    'tcl',
    'doc',
]

STDLIB_TO_PRUNE = [
    'test', 'unittest', 'tkinter', 'idlelib', 'turtledemo', 'turtle.py', 
    'ensurepip', 'pydoc_data', 'venv', 'lib2to3', 'ctypes/test', 'distutils/tests',
    'curses', 'dbm', 'pydoc.py', 'doctest.py', 'zipapp.py'
]

PACKAGES_TO_PRUNE = [
    'pip', 'setuptools', 'wheel',
    'PIL', 'Pillow',
    'lxml', 'cryptography', 'ecdsa',
    # Add other known unused heavy packages here
]

KEEP_DIALECTS = ['ardupilotmega', 'common', 'standard', 'minimal']

def get_python_lib_dir(platform_dir):
    """Find the lib directory depending on platform structure."""
    if 'windows' in platform_dir:
        return os.path.join(platform_dir, 'Lib')
    else:
        # mac/linux: find lib/python3.x
        lib_base = os.path.join(platform_dir, 'python', 'lib')
        if not os.path.exists(lib_base):
             # sometimes it's directly in lib?
             lib_base = os.path.join(platform_dir, 'lib')
        
        if os.path.exists(lib_base):
            # find python3.x subdir
            for d in os.listdir(lib_base):
                if d.startswith('python3.'):
                    return os.path.join(lib_base, d)
    return None

def usage():
    print("Usage: python3 optimize_python.py <platform_dir>")
    print("Example: python3 optimize_python.py python/macos")
    sys.exit(1)

def cleanup(platform_dir):
    if not os.path.exists(platform_dir):
        print(f"Directory not found: {platform_dir}")
        return

    print(f"Optimizing Python runtime in: {platform_dir}")
    
    # 1. Remove Top-Level Bloat
    for item in PATHS_TO_PRUNE:
        path = os.path.join(platform_dir, item)
        if os.path.exists(path):
            print(f"Removing {item}...")
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)

    # 2. Find Lib Directory
    lib_dir = get_python_lib_dir(platform_dir)
    if not lib_dir or not os.path.exists(lib_dir):
        print("Could not locate python lib directory. Aborting lib cleanup.")
        return
    print(f"Found lib dir: {lib_dir}")

    # 3. Remove Standard Library Bloat
    for item in STDLIB_TO_PRUNE:
        path = os.path.join(lib_dir, item)
        if os.path.exists(path):
            print(f"Removing lib/{item}...")
            if os.path.isdir(path): shutil.rmtree(path)
            else: os.remove(path)

    # 4. Clean Site-Packages
    site_packages = os.path.join(lib_dir, 'site-packages')
    if os.path.exists(site_packages):
        for item in PACKAGES_TO_PRUNE:
            path = os.path.join(site_packages, item)
            # check for .dist-info too
            dist_info = glob.glob(os.path.join(site_packages, f"{item}-*.dist-info"))
            
            if os.path.exists(path):
                print(f"Removing package {item}...")
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            
            for di in dist_info:
                print(f"Removing {os.path.basename(di)}...")
                shutil.rmtree(di)

        # 5. Optimize Pymavlink
        pymavlink_dir = os.path.join(site_packages, 'pymavlink', 'dialects')
        if os.path.exists(pymavlink_dir):
            print("Optimizing pymavlink dialects...")
            
            for ver in ['v10', 'v20']:
                v_dir = os.path.join(pymavlink_dir, ver)
                if os.path.exists(v_dir):
                    # remove __pycache__ specifically first which is huge here
                    pycache = os.path.join(v_dir, '__pycache__')
                    if os.path.exists(pycache): shutil.rmtree(pycache)
                    
                    for f in os.listdir(v_dir):
                        if f.endswith('.py') or f.endswith('.xml'):
                            name = f.replace('.py', '').replace('.xml', '')
                            if name not in KEEP_DIALECTS and name != '__init__':
                                os.remove(os.path.join(v_dir, f))

    # 6. Global Pycache Cleanup
    print("Removing __pycache__ everywhere...")
    for root, dirs, files in os.walk(platform_dir):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d))
        # also remove .pyc files not in __pycache__ just in case
        for f in files:
            if f.endswith('.pyc') or f.endswith('.pyo'):
                os.remove(os.path.join(root, f))

    print("Optimization Complete.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
    cleanup(sys.argv[1])
