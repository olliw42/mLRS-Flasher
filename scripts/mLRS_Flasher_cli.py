#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
# OlliW @ www.olliw.eu
# ************************************************************
# mLRS flasher cli - JSON interface for Electron
# 2026-01-11 (v0.3.0)
# ************************************************************
# command line interface for mLRS flasher, designed to be called
# from Electron via child_process.spawn()
# ************************************************************

import os
import sys
import time
import json
import argparse
import subprocess
import re
import copy
import tempfile

# resolve paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# ************************************************************
# Constants
# ************************************************************

if sys.platform == 'darwin':
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'mac', 'bin', 'STM32_Programmer_CLI')
elif sys.platform == 'linux':
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'linux', 'bin', 'STM32_Programmer_CLI')
else:
    STM32_PROG_PATH = os.path.join(ROOT_DIR, 'thirdparty', 'STM32CubeProgrammer', 'win', 'bin', 'STM32_Programmer_CLI.exe')

ESPTOOL_PATH = os.path.normpath(os.path.join(ROOT_DIR, 'thirdparty', 'esptool', 'esptool.py'))
ASSETS_PATH = os.path.normpath(os.path.join(ROOT_DIR, 'assets'))

# add thirdparty to path for pymavlink
sys.path.insert(0, os.path.join(ROOT_DIR, 'thirdparty', 'mavlink'))

import requests
import serial
from serial.tools.list_ports import comports

# import metadata
sys.path.insert(0, os.path.join(ROOT_DIR, 'assets'))
import mLRS_metadata as mlrs_md

# import passthrough scripts (add scripts dir to path for embedded python)
sys.path.insert(0, SCRIPT_DIR)
import apInitPassthru as appassthru
import edgetxInitPassthru as radio

# Disable blocking prompts in passthrough scripts
appassthru.PAUSE_ON_EXIT = False
radio.PAUSE_ON_EXIT = False


# ************************************************************
# JSON output helpers
# ************************************************************

def json_output(data):
    """output a json object to stdout"""
    print(json.dumps(data), flush=True)


def json_log(message, log_type='log'):
    """output a log message in json format"""
    json_output({'type': log_type, 'message': str(message)})


def json_progress(percent, message=''):
    """output progress update"""
    json_output({'type': 'progress', 'percent': percent, 'message': message})


def json_error(message):
    """output an error message"""
    json_log(message, 'error')


def json_success(message):
    """output a success message"""
    json_log(message, 'success')


# ensure stdout is unbuffered if possible
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass


# USB VID/PID constants for device filtering
VID_STMICRO = 0x0483
PID_STLINK = 0x374E
PID_EDGETX_OPENTX = 0x5740
VID_ARDUPILOT = 0x1209
PID_ARDUPILOT_1 = 0x5740
PID_ARDUPILOT_2 = 0x5741



# ************************************************************
# Output helpers
# ************************************************************

def strip_ansi(text):
    """strip ANSI escape codes and partial fragments from CR-split lines"""
    # full ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    return text


def is_ansi_garbage(text):
    """check if line is just ANSI escape code fragments (not meaningful output)"""
    stripped = text.strip()
    # match lines that are just partial ANSI codes like "[00;" or "32m" etc
    if re.match(r'^\[\d+;', stripped):  # [00; followed by anything
        return True
    if re.match(r'^\d+m\[', stripped):  # 32m[ - color code before progress bar
        return True
    if re.match(r'^\d+m$', stripped):   # just "32m" alone
        return True
    return False


def monitor_process(proc, progress_regex=None):
    """monitor a subprocess and parse progress"""
    last_percent = -1
    
    for line in read_lines_with_cr(proc.stdout):
        clean_line = strip_ansi(line).strip()
        if not clean_line:
            continue
            
        # update smooth progress bar if regex provided
        if progress_regex:
            match = re.search(progress_regex, clean_line)
            if match:
                percent = int(match.group(1))
                if percent != last_percent:
                    json_progress(percent, 'Flashing...')
                    last_percent = percent
        
        # skip logging ANSI garbage lines (partial escape codes)
        if is_ansi_garbage(clean_line):
            continue
        
        # log meaningful lines to console
        json_log(clean_line)
    
    proc.wait()
    return proc.returncode


def read_lines_with_cr(stream):
    """yield lines from stream, splitting on \n or \r"""
    buf = bytearray()
    while True:
        # read one byte at a time for maximum responsiveness
        char = stream.read(1)
        if not char:
            if buf:
                yield buf.decode('utf-8', errors='ignore')
            break
        if char == b'\r' or char == b'\n':
            if buf:
                yield buf.decode('utf-8', errors='ignore')
                buf = bytearray()
        else:
            buf.extend(char)
            # safety: yield if buffer gets too long (e.g. no newlines)
            if len(buf) > 4096:
                yield buf.decode('utf-8', errors='ignore')
                buf = bytearray()


# ************************************************************
# API helper functions (from original mLRS_Flasher.py)
# ************************************************************

g_TxModuleExternal_minimal_version = 'v1.3.00'
g_Receiver_minimal_version = 'v1.3.00'
g_TxModuleInternal_minimal_version = 'v1.3.05'
g_LuaScript_minimal_version = 'v1.3.00'

g_firmware_json_url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/tools/web/mlrs_firmware_urls.json'
g_repository_url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/'
g_main_branch_url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/main'
g_wirelessbridge_path_url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/firmware/wirelessbridge/'

g_jsonCacheDict = {}


def request_json_dict(url, extension='', error_msg=''):
    """request json from url with caching"""
    if url in g_jsonCacheDict:
        return copy.deepcopy(g_jsonCacheDict[url])
    
    json_log(f'Fetching {url}...')
    res = None
    tries = 4
    while tries > 0:
        try:
            res = requests.get(url + extension, allow_redirects=True, timeout=(3.05, 15))
            if b'API rate limit exceeded' in res.content:
                json_error('GitHub API rate limit exceeded')
                return None
            json_dict = res.json()
            break
        except Exception:
            tries -= 1
            if tries <= 0:
                json_error(f'Failed to fetch {url}')
                return None
    
    g_jsonCacheDict[url] = copy.deepcopy(json_dict)
    return json_dict


def request_data(url, error_msg=''):
    """request binary/text data from url"""
    json_log(f'Downloading {url}...')
    tries = 4
    while tries > 0:
        try:
            res = requests.get(url, allow_redirects=True, timeout=(3.05, 15))
            if b'API rate limit exceeded' in res.content:
                json_error('GitHub API rate limit exceeded')
                return None
            try:
                json_dict = res.json()
                if json_dict.get('encoding') == 'base64':
                    import base64
                    return base64.b64decode(json_dict['content'])
                return json_dict['content']
            except Exception:
                return res.content
        except Exception as e:
            tries -= 1
            if tries <= 0:
                json_error(f'Failed to download: {e}')
                return None
    return None


def resolve_chipset(device_dict, target_dict, filename):
    """resolve chipset from device and target metadata"""
    chipset = device_dict.get('chipset', 'stm32')
    
    # check for target-specific overrides (top-level)
    if 'chipset' in target_dict:
        chipset = target_dict['chipset']
        
    # check for file-specific overrides
    for key in target_dict:
        if key in filename:
            sub_val = target_dict[key]
            if isinstance(sub_val, dict) and 'chipset' in sub_val:
                chipset = sub_val['chipset']
            break
            
    return chipset


# ************************************************************
# Command handlers
# ************************************************************

def cmd_list_versions(args):
    """list available firmware versions"""
    res = request_json_dict(g_firmware_json_url, '', 'Failed to get versions')
    if not res:
        json_output({'versions': []})
        return
    
    versions = []
    for key in res.keys():
        v = key.split('.')
        patch = int(v[2])
        if patch == 0:
            version_str = key + ' (release)'
        elif patch & 1 == 0:
            version_str = key + ' (pre-release)'
        else:
            version_str = key + ' (dev)'
        
        versions.append({
            'version': key,
            'versionStr': version_str,
            'commit': res[key].get('commit', ''),
            'gitUrl': g_repository_url + res[key].get('commit', ''),
        })
    
    # try to get dev version from main branch
    main_res = request_json_dict(g_main_branch_url, '', '')
    if main_res:
        tree = main_res.get('tree', [])
        for item in tree:
            if item.get('path') == 'firmware':
                firmware_url = item.get('url', '')
                if firmware_url:
                    firmware_res = request_json_dict(firmware_url, '?recursive=true', '')
                    if firmware_res:
                        for f in firmware_res.get('tree', []):
                            if '-@' in f.get('path', ''):
                                match = re.search(r'-(v\d\.\d+?\.\d+?-@[A-Za-z0-9]+?)\.', f['path'])
                                if match:
                                    dev_version = match.group(1)
                                    versions.append({
                                        'version': dev_version,
                                        'versionStr': dev_version + ' (dev)',
                                        'gitUrl': firmware_url,
                                    })
                                break
                break
    
    json_output({'versions': versions})


def get_git_url_for_version(version):
    """resolve git url for a version string"""
    if version == 'main':
        return g_main_branch_url
    
    # get versions list
    versions_res = request_json_dict(g_firmware_json_url, '', '')
    if not versions_res:
        return None
        
    # strip off any commit hash for lookup
    base_version = version.split('-@')[0] if '-@' in version else version
    
    if base_version in versions_res:
        return g_repository_url + versions_res[base_version].get('commit', '')
    else:
        # might be a dev version, try main branch logic
        # For simplicity, if not found and not main, we fall back to main search or fail
        pass
    
    return None


def cmd_list_devices(args):
    """list available device types"""
    device_type = args.type
    
    if device_type == 'tx':
        devices = list(mlrs_md.g_txModuleExternalDeviceTypeDict.keys())
    elif device_type == 'rx':
        devices = list(mlrs_md.g_receiverDeviceTypeDict.keys())
    elif device_type == 'txint':
        devices = list(mlrs_md.g_txModuleInternalDeviceTypeDict.keys())
    else:
        json_error(f'Unknown device type: {device_type}')
        devices = []
    
    json_output({'devices': devices})


def cmd_list_firmware(args):
    """list firmware files for a device/version"""
    # get the git url for this version
    version = args.version
    
    if version == 'main':
        git_url = g_main_branch_url
    else:
        # strip off any commit hash for lookup
        versions_res = request_json_dict(g_firmware_json_url, '', '')
        if not versions_res:
            json_output({'files': []})
            return

        base_version = version.split('-@')[0] if '-@' in version else version
        
        if base_version in versions_res:
            git_url = g_repository_url + versions_res[base_version].get('commit', '')
        else:
            # might be a dev version, try main branch
            main_res = request_json_dict(g_main_branch_url, '', '')
            if main_res:
                for item in main_res.get('tree', []):
                    if item.get('path') == 'firmware':
                        git_url = item.get('url', '')
                        break
            else:
                json_output({'files': []})
                return
    
    # get file list from tree
    tree_res = request_json_dict(git_url, '?recursive=true', '')
    if not tree_res:
        json_output({'files': []})
        return
    
    # get device info
    device = args.device
    if args.type == 'tx':
        device_dict = mlrs_md.g_txModuleExternalDeviceTypeDict.get(device, {})
    elif args.type == 'rx':
        device_dict = mlrs_md.g_receiverDeviceTypeDict.get(device, {})
    elif args.type == 'txint':
        device_dict = mlrs_md.g_txModuleInternalDeviceTypeDict.get(device, {})
    elif args.type == 'lua':
        device_dict = {}
    else:
        device_dict = {}
    
    fname = device_dict.get('fname', '')
    
    # filter files
    files = []
    for item in tree_res.get('tree', []):
        path = item.get('path', '')
        if item.get('type') != 'blob':
            continue
        
        # Lua script filtering
        if args.type == 'lua':
            if 'lua/' not in path or not path.endswith('.lua'):
                continue
            
            filename = os.path.basename(path)
            files.append({
                'filename': filename,
                'path': path,
                'url': item.get('url', ''),
            })
            continue

        if 'firmware/' not in path and 'pre-release' not in path:
            continue
        if fname and fname not in path:
            continue
        if args.type == 'txint' and '-internal-' not in path:
            continue
        if args.type != 'txint' and '-internal-' in path:
            continue
        
        filename = os.path.basename(path)
        files.append({
            'filename': filename,
            'path': path,
            'url': item.get('url', ''),
        })
    
    json_output({'files': files})


def find_serial_ports_usbttl_devices():
    """find serial ports for USB-TTL devices, filtering out known non-serial devices"""
    try:
        port_list = list(comports())
    except Exception:
        return []
    
    device_ports = []
    for port in port_list:
        if 'USB' not in port.hwid.upper():
            continue
        # skip STLink debugger
        if port.vid == VID_STMICRO and port.pid == PID_STLINK:
            continue
        # skip EdgeTX/OpenTX radio serial
        if port.vid == VID_STMICRO and port.pid == PID_EDGETX_OPENTX:
            continue
        # skip ArduPilot serial
        if port.vid == VID_ARDUPILOT and port.pid in (PID_ARDUPILOT_1, PID_ARDUPILOT_2):
            continue
        device_ports.append(port.device)
    return device_ports


def cmd_list_ports(args):
    """list available serial ports with optional filtering"""
    try:
        port_type = getattr(args, 'port_type', 'default')
        if port_type in ('esp,tx', 'esp,usbttl'):
            ports = find_serial_ports_usbttl_devices()
        else:
            port_list = list(comports())
            ports = [port.device for port in port_list]
        json_output({'ports': ports})
    except Exception as e:
        json_error(f'Failed to list ports: {e}')
        json_output({'ports': []})


def cmd_get_metadata(args):
    """get metadata for a device/file"""
    device = args.device
    filename = args.filename
    device_type = args.type
    
    # get device dict
    if device_type == 'tx':
        device_dict = mlrs_md.g_txModuleExternalDeviceTypeDict.get(device, {})
        target_dict = mlrs_md.g_targetDict.get(device_dict.get('fname', ''), {})
    elif device_type == 'rx':
        device_dict = mlrs_md.g_receiverDeviceTypeDict.get(device, {})
        target_dict = mlrs_md.g_targetDict.get(device_dict.get('fname', ''), {})
    elif device_type == 'txint':
        device_dict = mlrs_md.g_txModuleInternalDeviceTypeDict.get(device, {})
        target_dict = mlrs_md.g_targetDict.get(device_dict.get('fname', ''), {})
    else:
        json_output({})
        return
    
    # resolve chipset using helper
    chipset = resolve_chipset(device_dict, target_dict, filename)
    
    flashmethod = target_dict.get('flashmethod', 'stlink')
    description = target_dict.get('description', '')
    wireless = target_dict.get('wireless')
    
    # check for target-specific overrides for other properties
    for key in target_dict:
        if key in filename:
            sub_dict = target_dict[key]
            # chipset already resolved
            if 'flashmethod' in sub_dict:
                flashmethod = sub_dict['flashmethod']
            if 'description' in sub_dict:
                description = sub_dict['description']
            if 'wireless' in sub_dict:
                wireless = sub_dict['wireless']
            break
    
    # determine programmer string
    if 'stm32' in chipset:
        if 'dfu' in flashmethod:
            programmer = 'stm32 dfu'
        elif 'uart' in flashmethod:
            programmer = 'stm32 uart'
        else:
            programmer = 'stm32 stlink'
    else:
        programmer = chipset

    # determine if port is needed
    if device_type == 'txint':
        # internal modules use auto-detection via radio passthrough
        needs_port = False
        # ensure programmer string triggers internal logic if not redundant
        if 'internal' not in programmer and 'stm32' not in programmer:
             programmer += ' internal'
    else:
        needs_port = 'uart' in flashmethod or 'esptool' in flashmethod or 'esp' in programmer
    
    json_output({
        'chipset': chipset,
        'flashmethod': flashmethod,
        'raw_flashmethod': flashmethod, # expose raw string for UI parsing
        'description': description,
        'needsPort': needs_port,
        'programmer': programmer,
        'hasWirelessBridge': wireless is not None,
    })


def cmd_flash(args):
    """flash firmware to device"""
    json_log('Starting flash operation...')
    
    # create temp directory in system temp
    temp_dir = os.path.join(tempfile.gettempdir(), 'mLRS-Flasher')
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir)
        except Exception as e:
            json_error(f'Failed to create temp directory {temp_dir}: {e}')
            return
    
    url = args.url
    filename = args.filename
    # inputs
    provided_programmer = args.programmer
    device_name = getattr(args, 'device', None)
    flash_method = getattr(args, 'flash_method', None)
    
    extra_args = {}
    
    # --------------------------------------------------------------------------
    # Programmer Resolution Logic
    # --------------------------------------------------------------------------
    # The goal is to determine the final 'programmer' string and any 'extra_args'
    # based on the device and method, instead of relying on the UI to send it.

    programmer = provided_programmer # default to what was passed if we can't resolve it

    # if 'auto' or basic method passed, try to resolve full programmer string from metadata
    if device_name and flash_method:
        json_log(f'Resolving programmer for device: {device_name}, method: {flash_method}')
        
        # 1. Resolve Device Dictionary
        # (Reuse logic from cmd_get_metadata essentially, but simplified lookup)
        device_dict = {}
        target_dict = {}
        
        # search in all dicts
        for dev_dict in [mlrs_md.g_txModuleExternalDeviceTypeDict, 
                         mlrs_md.g_receiverDeviceTypeDict, 
                         mlrs_md.g_txModuleInternalDeviceTypeDict]:
            if device_name in dev_dict:
                device_dict = dev_dict.get(device_name, {})
                fname = device_dict.get('fname', '')
                target_dict = mlrs_md.g_targetDict.get(fname, {})
                break
        
        if not device_dict:
             json_log(f'Warning: Device {device_name} not found in metadata, using provided programmer: {provided_programmer}')
        else:
            # 1. Resolve Device Dictionary (re-used logic)
            # ... (lines 603-614 are loop to find device_dict, not touching that part yet unless needed)
            
            # Use helper to resolve chipset
            chipset = resolve_chipset(device_dict, target_dict, filename)

            # 2. Construct Programmer String
            resolved_programmer = ''
            
            if 'stm32' in chipset:
                if 'dfu' in flash_method:
                    resolved_programmer = 'stm32 dfu'
                elif 'uart' in flash_method:
                    resolved_programmer = 'stm32 uart'
                elif 'appassthru' in flash_method:
                    # appassthru requires serial port index, usually passed in via provided_programmer
                    # or needs to be constructed. 
                    # If the UI sent "appassthru", we expect it might not have sent the full string yet
                    # BUT existing UI sends `stm32 appassthru serialX`.
                    # Let's see if we can preserve the serial part if provided in the legacy arg
                    if provided_programmer and 'serial' in provided_programmer.lower():
                         if not provided_programmer.lower().startswith('stm32 '):
                             resolved_programmer = 'stm32 ' + provided_programmer
                         else:
                             resolved_programmer = provided_programmer
                    else:
                         # fallback if we don't have serial info yet (should catch this later)
                         resolved_programmer = 'stm32 appassthru'
                else:
                    resolved_programmer = 'stm32 stlink'
            elif 'esp' in chipset:
                if 'appassthru' in flash_method:
                    if provided_programmer and 'serial' in provided_programmer.lower():
                         if not provided_programmer.lower().startswith(chipset) and not provided_programmer.lower().startswith('esp'):
                             resolved_programmer = f'{chipset} {provided_programmer}'
                         else:
                             resolved_programmer = provided_programmer
                    else:
                         resolved_programmer = f'{chipset} appassthru'
                else:
                    # Generic ESP handling
                    # check for specific reset requirements (e.g. 'no dtr')
                    # This logic was previously in the UI. Now we access it here.
                    
                    # We need to dig into the target_dict again to find any 'wireless' block 
                    # OR specific notes. However, main firmware usually uses default reset.
                    # Wireless bridge logic is handled separately below.
                    resolved_programmer = chipset
            
            if resolved_programmer:
                programmer = resolved_programmer
                json_log(f'Resolved programmer to: {programmer}')
    
    # --------------------------------------------------------------------------
    
    # helper to ensure safe string op
    if programmer is None:
        programmer = ''

    # extract serialx_no if present
    serialx_no = None
    f = re.search(r' serial([0-9]+?)', programmer.lower())
    if f:
        serialx_no = int(f.group(1))

    # resolve wireless bridge chipset and firmware
    # (This logic remains largely similar but we ensure it works with the new args)
    if 'wireless' in (flash_method or '') or 'wirelessbridge' in programmer.lower():
        programmer = 'esp wirelessbridge' # standardize if entering this block
        found_chipset = None
        found_baud = None
        
        # find the longest matching top-level key to ensure specific entries
        # (e.g. 'tx-radiomaster-internal') are matched over shorter ones (e.g. 'tx-radiomaster')
        best_key = None
        best_key_len = 0
        for key in mlrs_md.g_targetDict.keys():
            if key in filename and len(key) > best_key_len:
                best_key = key
                best_key_len = len(key)
        
        if best_key:
            val = mlrs_md.g_targetDict[best_key]
            # check for default wireless
            if isinstance(val, dict):
                if 'wireless' in val:
                    found_chipset = val['wireless'].get('chipset')
                    found_baud = val['wireless'].get('baud')
                    if 'reset' in val['wireless']: extra_args['reset'] = val['wireless']['reset']
                    if 'erase' in val['wireless']: extra_args['erase'] = val['wireless']['erase']

                # check overrides - find longest matching sub-key
                best_match = None
                best_match_len = 0
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, dict) and sub_key in filename:
                        if len(sub_key) > best_match_len:
                            best_match = (sub_key, sub_val)
                            best_match_len = len(sub_key)
                
                if best_match:
                    sub_key, sub_val = best_match
                    if 'wireless' in sub_val:
                        found_chipset = sub_val['wireless'].get('chipset')
                        found_baud = sub_val['wireless'].get('baud')
                        if 'reset' in sub_val['wireless']: extra_args['reset'] = sub_val['wireless']['reset']
                        if 'erase' in sub_val['wireless']: extra_args['erase'] = sub_val['wireless']['erase']
        
        if found_chipset:
            # the wireless chipset is in wireless['chipset'], not chipset
            if 'esp32c3' in found_chipset:
                filename = 'mlrs-wireless-bridge-esp32c3.ino.bin'
            elif 'esp8266' in found_chipset or 'esp8285' in found_chipset or 'esp8255' in found_chipset:
                filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
            else:
                json_error(f'Unsupported wireless bridge chipset: {found_chipset}')
                sys.exit(1)
            
            url = g_wirelessbridge_path_url + filename
            programmer = found_chipset
            
            json_log(f'Resolved wireless bridge firmware: {filename}')
            if found_baud:
                args.baudrate = found_baud
                json_log(f'Set baudrate to {args.baudrate}')
        else:
            json_log('Warning: Could not resolve wireless bridge chipset, defaulting to esp8266')
            programmer = 'esp8266'
            filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
            url = g_wirelessbridge_path_url + filename

    # handle passthrough initialization
    comport = args.port
    baudrate = args.baudrate

    if 'appassthru' in programmer.lower():
        if serialx_no is None:
            # try to find default if implied by device type? For now, stick to error.
            json_error('ArduPilot passthrough requires a serial port number (e.g. serial2)')
            return
        json_log(f'Initializing ArduPilot passthrough on SERIAL{serialx_no}...')
        try:
            init_baud = baudrate if baudrate > 0 else 57600
            options = []
            if 'esp' in programmer.lower():
                options = ['nosysboot', 'scripting']
            comport, passthru_baud = appassthru.mlrs_open_passthrough(comport, init_baud, serialx_no, options)
            json_log(f'Passthrough established on {comport} at {passthru_baud}')
            baudrate = passthru_baud
            time.sleep(5.0) 
        except Exception as e:
            json_error(f'Failed to open ArduPilot passthrough: {e}')
            return

    elif args.type == 'txint' or 'internal' in programmer.lower():
        json_log('Initializing EdgeTX passthrough for internal module...')
        try:
            is_bridge = 'wirelessbridge' in (flash_method or '').lower() or 'wirelessbridge' in provided_programmer.lower()
            if baudrate <= 0:
                baudrate = 115200 if is_bridge else 921600
            comport = radio.open_passthrough(comport=comport, baudrate=baudrate, wirelessbridge=is_bridge)
            json_log(f'Passthrough established on {comport}')
        except Exception as e:
            json_error(f'Failed to open EdgeTX passthrough: {e}')
            return

    # download firmware file
    json_log(f'Final Flash Config -> Programmer: {programmer}, File: {filename}, Port: {comport}')
    json_progress(10, 'Downloading firmware...')
    data = request_data(url)
    if not data:
        json_error('Failed to download firmware')
        return
    
    filepath = os.path.join(temp_dir, os.path.basename(filename))
    
    try:
        with open(filepath, 'wb') as f:
            f.write(data)
        json_log(f'Saved firmware to {filepath}')
        
        json_progress(30, 'Starting flash...')
        
        # determine flash tool and args
        success = False
        if 'stm32' in programmer.lower():
            success = flash_stm32(programmer, filepath, comport, baudrate)
        elif 'esp' in programmer.lower():
            success = flash_esp(programmer, filepath, comport, baudrate, extra_args)
        else:
            json_error(f'Unknown programmer: {programmer}')
            sys.exit(1)
            
        if not success:
            sys.exit(1)
        
        json_progress(100, 'Complete')
        json_success('Flash operation completed!')
        
    finally:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                # json_log('Cleaned up temp file')
            except Exception:
                pass


def flash_stm32(programmer, firmware, comport, baudrate):
    """flash STM32 using STM32CubeProgrammer"""
    
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
    
    # monitor process with progress regex for STM32
    # output: ... (45%) ...
    returncode = monitor_process(proc, r'(\d+)%')
    
    if returncode != 0:
        json_error(f'STM32CubeProgrammer exited with code {returncode}')
        return False
    
    return True


def flash_esp(programmer, firmware, comport, baudrate, extra_args=None):
    """flash ESP using esptool"""
    if not baudrate:
        baudrate = 921600
        
    if not os.path.exists(ESPTOOL_PATH):
        json_error(f'esptool not found at {ESPTOOL_PATH}')
        return False
    
    if not comport:
        json_error("No COM port selected. Please select a COM port.")
        return False

    # determine chip type and args
    if extra_args is None: extra_args = {}
    
    before_mode = 'default_reset'
    if extra_args.get('reset') == 'no dtr' or 'no dtr' in programmer.lower():
        before_mode = 'no_reset'
    
    erase_args = []
    if extra_args.get('erase') == 'full_erase':
        erase_args = ['-e']

    # Common base arguments
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

    # Defaults for unknown chips (fallback)
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
                # compare with v1.3.07
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
        # esp8266 uses simpler args, doesn't need flash_mode/freq/size for write_flash mostly?
        # Re-constructing exact previous behavior:
        # previous: --chip esp8266 --port .. --baud .. --before .. --after .. write_flash [-e] 0x0 fw
        
        # Reuse base_args but strip the flash params which weren't in the original block for 8266?
        # Original 8266 block:
        # args = ['--chip', chip, '--port', ..., '--after', 'hard_reset', 'write_flash'] + e_args + ['0x0', firmware]
        # It did NOT have -z, --flash_mode, --flash_freq, --flash_size.
        
        # Let's handle 8266 separately to preserve exact behavior, or carefully construct.
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
    
    # Construct final args for ESP32 variants
    if chip != 'esp8266':
         args = ['--chip', chip] + base_args + ['--flash_size', flash_size] + bootloader_images

    json_log(f'Running esptool for {chip}...')
    
    # run esptool
    # ensure unbuffered output
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # shim to bypass Windows PYTHONPATH ignoring in embedded distributions.
    esptool_dir = os.path.dirname(ESPTOOL_PATH)
    shim = "import sys, os; sys.path.insert(0, sys.argv.pop(1)); sys.argv[0] = 'esptool'; import esptool; esptool._main()"
    cmd = [sys.executable, '-u', '-c', shim, esptool_dir] + args
    
    # json_log(f"debug: launching with shim -> {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=0
    )
    
    # Simple debug to confirm start
    json_log(f'Esptool started with args: {args}')

    # monitor process with progress regex for esptool
    # output: ... (10 %) ...
    returncode = monitor_process(proc, r'\((\d+)\s*%\)')

    if returncode != 0:
        json_error(f'esptool exited with code {returncode}')
        return False
        
    return True


def cmd_download_lua(args):
    """download lua scripts"""
    json_log('Downloading Lua scripts...')
    
    # get file list from version
    version = args.version
    
    if version == 'main':
        git_url = g_main_branch_url
    else:
        versions_res = request_json_dict(g_firmware_json_url, '', '')
        if not versions_res:
            json_error('Failed to get versions')
            return

        base_version = version.split('-@')[0] if '-@' in version else version
        
        if base_version in versions_res:
            git_url = g_repository_url + versions_res[base_version].get('commit', '')
        else:
            json_error(f'Version {version} not found')
            return
    
    # get tree
    tree_res = request_json_dict(git_url, '?recursive=true', '')
    if not tree_res:
        json_error('Failed to get file tree')
        return
    
    # find lua files
    output_dir = args.output or os.path.join(ROOT_DIR, 'lua-scripts')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    target_filename = args.filename
    if target_filename and target_filename.lower() == 'all':
        target_filename = None

    downloaded_count = 0
    for item in tree_res.get('tree', []):
        path = item.get('path', '')
        if 'lua/' in path and '.lua' in path and item.get('type') == 'blob':
            filename = os.path.basename(path)
            
            # if specific file requested, skip others
            if target_filename and filename != target_filename:
                continue

            data = request_data(item.get('url', ''))
            if data:
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(data)
                json_log(f'Saved {filename}')
                downloaded_count += 1
    
    if downloaded_count == 0:
        if target_filename:
            json_error(f'File {target_filename} not found')
        else:
            json_error('No Lua scripts found')
    else:
        json_success(f'Downloaded {downloaded_count} script(s) to {output_dir}')


# ************************************************************
# Main entry point
# ************************************************************

def main():
    parser = argparse.ArgumentParser(description='mLRS Flasher CLI')
    parser.add_argument('--json', action='store_true', help='JSON output mode (always enabled)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # list-versions
    subparsers.add_parser('list-versions', help='List available firmware versions')
    
    # list-devices
    p = subparsers.add_parser('list-devices', help='List available device types')
    p.add_argument('--type', choices=['tx', 'rx', 'txint'], required=True)
    
    # list-firmware
    p = subparsers.add_parser('list-firmware', help='List firmware files')
    p.add_argument('--type', choices=['tx', 'rx', 'txint', 'lua'], required=True)
    p.add_argument('--device', required=False)
    p.add_argument('--version', required=True)
    
    # list-ports
    p = subparsers.add_parser('list-ports', help='List available serial ports')
    p.add_argument('--port-type', choices=['default', 'esp,tx', 'esp,usbttl'], default='default')
    
    # get-metadata
    p = subparsers.add_parser('get-metadata', help='Get metadata for device/file')
    p.add_argument('--type', choices=['tx', 'rx', 'txint'], required=True)
    p.add_argument('--device', required=True)
    p.add_argument('--filename', required=True)
    
    # flash
    p = subparsers.add_parser('flash', help='Flash firmware to device')
    p.add_argument('--type', choices=['tx', 'rx', 'txint'], required=True)
    p.add_argument('--programmer', required=False, help='Legacy programmer string (optional)')
    p.add_argument('--device', required=False, help='Device name for lookup')
    p.add_argument('--flash-method', required=False, help='Flash method (dfu, uart, etc)')
    p.add_argument('--url', required=True)
    p.add_argument('--filename', required=True)
    p.add_argument('--port', required=False)
    p.add_argument('--baudrate', type=int, default=0)
    
    # download-lua
    p = subparsers.add_parser('download-lua', help='Download Lua scripts')
    p.add_argument('--version', required=True)
    p.add_argument('--output', required=False)
    p.add_argument('--filename', required=False, help='Specific file to download or "all"')
    
    args = parser.parse_args()
    
    if args.command == 'list-versions':
        cmd_list_versions(args)
    elif args.command == 'list-devices':
        cmd_list_devices(args)
    elif args.command == 'list-firmware':
        cmd_list_firmware(args)
    elif args.command == 'list-ports':
        cmd_list_ports(args)
    elif args.command == 'get-metadata':
        cmd_get_metadata(args)
    elif args.command == 'flash':
        cmd_flash(args)
    elif args.command == 'download-lua':
        cmd_download_lua(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
