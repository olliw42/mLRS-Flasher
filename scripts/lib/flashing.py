#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import os
import sys
import time
import subprocess
import re
from .constants import SCRIPT_DIR, STM32_PROG_PATH, ESPTOOL_PATH, ASSETS_PATH
from .utils import json_log, json_error, json_progress, read_lines_with_cr, strip_ansi, is_ansi_garbage

# import passthrough scripts
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import apInitPassthru as appassthru
import edgetxInitPassthru as radio

# disable blocking prompts
appassthru.PAUSE_ON_EXIT = False
radio.PAUSE_ON_EXIT = False


# monitor a subprocess and parse progress
def monitor_process(proc, progress_regex=None):
    last_percent = -1
    
    for line in read_lines_with_cr(proc.stdout):
        clean_line = strip_ansi(line).strip()
        if not clean_line:
            continue
            
        # update smooth progress bar if regex provided
        if progress_regex:
            match = re.search(progress_regex, clean_line)
            if match:
                try:
                    percent = int(match.group(1))
                    if percent != last_percent:
                        json_progress(percent, 'Flashing...')
                        last_percent = percent
                except ValueError:
                    pass
        
        # skip logging ANSI garbage lines (partial escape codes)
        if is_ansi_garbage(clean_line):
            continue
        
        # log meaningful lines to console
        json_log(clean_line)
    
    proc.wait()
    return proc.returncode


# flash STM32 using STM32CubeProgrammer
def flash_stm32(programmer, firmware, comport, baudrate):
    
    if not os.path.exists(STM32_PROG_PATH):
        json_error(f'STM32CubeProgrammer not found at {STM32_PROG_PATH}')
        return False
    
    if not baudrate:
        baudrate = 115200
    
    # build args
    if 'dfu' in programmer:
        args = ['-c', 'port=usb1', '-w', firmware, '-v', '-g']
    elif 'uart' in programmer or 'appassthru' in programmer:
        args = ['-c', f'port={comport}', f'br={baudrate}', '-w', firmware, '-v', '-g']
    else:
        args = ['-c', 'port=SWD', 'freq=3900', '-w', firmware, '-v', '-g']
    
    json_log(f'Running: {STM32_PROG_PATH} {" ".join(args)}')
    
    # run programmer
    proc = subprocess.Popen(
        [STM32_PROG_PATH] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0
    )
    
    returncode = monitor_process(proc, r'(\d+)%')
    
    if returncode != 0:
        json_error(f'STM32CubeProgrammer exited with code {returncode}')
        return False
    
    return True


# flash ESP using esptool
def flash_esp(programmer, firmware, comport, baudrate, extra_args=None):
    if not baudrate:
        baudrate = 921600
        
    if not os.path.exists(ESPTOOL_PATH):
        json_error(f'esptool not found at {ESPTOOL_PATH}')
        return False
    
    if not comport:
        json_error("No COM port selected. Please select a COM port.")
        return False

    if extra_args is None: extra_args = {}
    
    before_mode = 'default_reset'
    if extra_args.get('reset') == 'no dtr' or 'no dtr' in programmer.lower():
        before_mode = 'no_reset'
    
    erase_args = []
    if extra_args.get('erase') == 'full_erase':
        erase_args = ['-e']

    # common base arguments
    base_args = [
        '--port', comport,
        '--baud', str(baudrate),
        '--before', before_mode,
        '--after', 'hard_reset',
        'write_flash'
    ] + erase_args + [
        '-z',
        '--flash_mode', 'dio',
        '--flash_freq', '40m'
    ]

    # defaults for unknown chips (fallback)
    chip = 'unknown'
    flash_size = '4MB'
    bootloader_images = []

    if 'esp32c3' in programmer:
        chip = 'esp32c3'
        flash_size = '4MB'
        bootloader_images = [
            '0x0000', os.path.join(ASSETS_PATH, 'esp32c3', 'bootloader.bin'),
            '0x8000', os.path.join(ASSETS_PATH, 'esp32c3', 'partitions.bin'),
            '0xe000', os.path.join(ASSETS_PATH, 'esp32c3', 'boot_app0.bin'),
            '0x10000', firmware,
        ]
    elif 'esp32s3' in programmer:
        chip = 'esp32s3'
        flash_size = '8MB'
        bootloader_images = [
            '0x0000', os.path.join(ASSETS_PATH, 'esp32s3', 'bootloader.bin'),
            '0x8000', os.path.join(ASSETS_PATH, 'esp32s3', 'partitions.bin'),
            '0xe000', os.path.join(ASSETS_PATH, 'esp32s3', 'boot_app0.bin'),
            '0x10000', firmware,
        ]
    elif 'esp32' in programmer:
        chip = 'esp32'
        flash_size = '4MB'
        
        # determine bootloader based on version
        bootloader_file = 'bootloader_40dio.bin'
        try:
            match = re.search(r'v(\d+)\.(\d+)\.(\d+)', os.path.basename(firmware))
            if match:
                major, minor, patch = map(int, match.groups())
                if (major, minor, patch) >= (1, 3, 7):
                    bootloader_file = 'bootloader_80qio.bin'
        except Exception:
            pass

        bootloader_images = [
            '0x1000', os.path.join(ASSETS_PATH, 'esp32', bootloader_file),
            '0x8000', os.path.join(ASSETS_PATH, 'esp32', 'partitions.bin'),
            '0xe000', os.path.join(ASSETS_PATH, 'esp32', 'boot_app0.bin'),
            '0x10000', firmware,
        ]
    elif 'esp8285' in programmer or 'esp8266' in programmer:
        chip = 'esp8266'
        args = [
            '--chip', chip,
            '--port', comport,
            '--baud', str(baudrate),
            '--before', before_mode,
            '--after', 'hard_reset',
            'write_flash'
        ] + erase_args + [
            '0x0', firmware,
        ]
    else:
        json_error(f'Unknown ESP chip in programmer: {programmer}')
        return False
    
    # construct final args for ESP32 variants
    if chip != 'esp8266':
         args = ['--chip', chip] + base_args + ['--flash_size', flash_size] + bootloader_images

    json_log(f'Running esptool for {chip}...')
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # shim to bypass Windows PYTHONPATH issues
    esptool_dir = os.path.dirname(ESPTOOL_PATH)
    shim = "import sys, os; sys.path.insert(0, sys.argv.pop(1)); sys.argv[0] = 'esptool'; import esptool; esptool._main()"
    cmd = [sys.executable, '-u', '-c', shim, esptool_dir] + args
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=0
    )
    
    returncode = monitor_process(proc, r'\((\d+)\s*%\)')

    if returncode != 0:
        json_error(f'esptool exited with code {returncode}')
        return False
        
    return True
