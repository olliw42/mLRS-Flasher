#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import os
import sys

# resolve paths relative to this script
LIB_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DIR = os.path.dirname(LIB_DIR)
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# ************************************************************
# tool paths
# ************************************************************

if sys.platform == 'darwin':
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'mac', 'bin', 'STM32_Programmer_CLI')
elif sys.platform == 'linux':
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'linux', 'bin', 'STM32_Programmer_CLI')
else:
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'win', 'bin', 'STM32_Programmer_CLI.exe')

ESPTOOL_PATH = os.path.normpath(os.path.join(ROOT_DIR, 'thirdparty', 'esptool', 'esptool.py'))
ASSETS_PATH = os.path.normpath(os.path.join(ROOT_DIR, 'assets'))

# ************************************************************
# USB VID/PID constants
# ************************************************************

VID_STMICRO = 0x0483
PID_STLINK = 0x374E
PID_EDGETX_OPENTX = 0x5740
VID_ARDUPILOT = 0x1209
PID_ARDUPILOT_1 = 0x5740
PID_ARDUPILOT_2 = 0x5741

# ************************************************************
# API URLs
# ************************************************************

FIRMWARE_JSON_URL = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/tools/web/mlrs_firmware_urls.json'
REPOSITORY_URL = 'https://api.github.com/repos/olliw42/mLRS/git/trees/'
MAIN_BRANCH_URL = 'https://api.github.com/repos/olliw42/mLRS/git/trees/main'
WIRELESSBRIDGE_PATH_URL = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/firmware/wirelessbridge/'

# ************************************************************
# versions
# ************************************************************

MINIMAL_VERSIONS = {
    'TxModuleExternal': 'v1.3.00',
    'Receiver': 'v1.3.00',
    'TxModuleInternal': 'v1.3.05',
    'LuaScript': 'v1.3.00',
}
