#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import os
import sys
import time
import re
import tempfile
from serial.tools.list_ports import comports

from .constants import (
    FIRMWARE_JSON_URL, REPOSITORY_URL, MAIN_BRANCH_URL, 
    WIRELESSBRIDGE_PATH_URL, ROOT_DIR, SCRIPT_DIR,
    VID_STMICRO, PID_STLINK, PID_EDGETX_OPENTX,
    VID_ARDUPILOT, PID_ARDUPILOT_1, PID_ARDUPILOT_2
)
from .utils import (
    json_output, json_log, json_error, json_success, json_progress
)
from .api import request_json_dict, request_data
from .metadata import resolve_chipset, get_device_info, mlrs_md
from .flashing import flash_stm32, flash_esp, appassthru, radio


# list available firmware versions
def cmd_list_versions(args):
    res = request_json_dict(FIRMWARE_JSON_URL, '', 'Failed to get versions')
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
            'gitUrl': REPOSITORY_URL + res[key].get('commit', ''),
        })
    
    # try to get dev version from main branch
    main_res = request_json_dict(MAIN_BRANCH_URL, '', '')
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


# list available device types
def cmd_list_devices(args):
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


# list firmware files for a device/version
def cmd_list_firmware(args):
    version = args.version
    
    if version == 'main':
        git_url = MAIN_BRANCH_URL
    else:
        versions_res = request_json_dict(FIRMWARE_JSON_URL, '', '')
        if not versions_res:
            json_output({'files': []})
            return

        base_version = version.split('-@')[0] if '-@' in version else version
        
        if base_version in versions_res:
            git_url = REPOSITORY_URL + versions_res[base_version].get('commit', '')
        else:
            main_res = request_json_dict(MAIN_BRANCH_URL, '', '')
            if main_res:
                for item in main_res.get('tree', []):
                    if item.get('path') == 'firmware':
                        git_url = item.get('url', '')
                        break
            else:
                json_output({'files': []})
                return
    
    tree_res = request_json_dict(git_url, '?recursive=true', '')
    if not tree_res:
        json_output({'files': []})
        return
    
    device_dict, _ = get_device_info(args.device, args.type)
    fname = device_dict.get('fname', '')
    
    files = []
    for item in tree_res.get('tree', []):
        path = item.get('path', '')
        if item.get('type') != 'blob':
            continue
        
        if args.type == 'lua':
            if 'lua/' not in path or not path.endswith('.lua'):
                continue
            filename = os.path.basename(path)
            files.append({'filename': filename, 'path': path, 'url': item.get('url', '')})
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
        files.append({'filename': filename, 'path': path, 'url': item.get('url', '')})
    
    json_output({'files': files})


# find serial ports for USB-TTL devices
def find_serial_ports_usbttl_devices():
    try:
        port_list = list(comports())
    except Exception:
        return []
    
    device_ports = []
    for port in port_list:
        if 'USB' not in port.hwid.upper():
            continue
        if port.vid == VID_STMICRO and port.pid == PID_STLINK:
            continue
        if port.vid == VID_STMICRO and port.pid == PID_EDGETX_OPENTX:
            continue
        if port.vid == VID_ARDUPILOT and port.pid in (PID_ARDUPILOT_1, PID_ARDUPILOT_2):
            continue
        device_ports.append(port.device)
    return device_ports


# list available serial ports
def cmd_list_ports(args):
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


# get metadata for a device/file
def cmd_get_metadata(args):
    device_dict, target_dict = get_device_info(args.device, args.type)
    
    if not device_dict:
        json_output({})
        return
    
    chipset = resolve_chipset(device_dict, target_dict, args.filename)
    flashmethod = target_dict.get('flashmethod', 'stlink')
    description = target_dict.get('description', '')
    wireless = target_dict.get('wireless')
    
    for key in target_dict:
        if key in args.filename:
            sub_dict = target_dict[key]
            if 'flashmethod' in sub_dict: flashmethod = sub_dict['flashmethod']
            if 'description' in sub_dict: description = sub_dict['description']
            if 'wireless' in sub_dict: wireless = sub_dict['wireless']
            break
    
    if 'stm32' in chipset:
        if 'dfu' in flashmethod: programmer = 'stm32 dfu'
        elif 'uart' in flashmethod: programmer = 'stm32 uart'
        else: programmer = 'stm32 stlink'
    else:
        programmer = chipset

    if args.type == 'txint':
        needs_port = False
        if 'internal' not in programmer and 'stm32' not in programmer:
             programmer += ' internal'
    else:
        needs_port = 'uart' in flashmethod or 'esptool' in flashmethod or 'esp' in programmer
    
    json_output({
        'chipset': chipset,
        'flashmethod': flashmethod,
        'raw_flashmethod': flashmethod,
        'description': description,
        'needsPort': needs_port,
        'programmer': programmer,
        'hasWirelessBridge': wireless is not None,
    })


# flash firmware to device
def cmd_flash(args):
    json_log('Starting flash operation...')
    
    temp_dir = os.path.join(tempfile.gettempdir(), 'mLRS-Flasher')
    if not os.path.exists(temp_dir):
        try: os.makedirs(temp_dir)
        except Exception as e:
            json_error(f'Failed to create temp directory {temp_dir}: {e}')
            return
    
    url = args.url
    filename = args.filename
    provided_programmer = args.programmer
    device_name = getattr(args, 'device', None)
    flash_method = getattr(args, 'flash_method', None)
    
    extra_args = {}
    programmer = provided_programmer or ''

    if device_name and flash_method:
        json_log(f'Resolving programmer for device: {device_name}, method: {flash_method}')
        device_dict, target_dict = get_device_info(device_name)
        
        if device_dict:
            chipset = resolve_chipset(device_dict, target_dict, filename)
            resolved_programmer = ''
            
            if 'stm32' in chipset:
                if 'dfu' in flash_method: resolved_programmer = 'stm32 dfu'
                elif 'uart' in flash_method: resolved_programmer = 'stm32 uart'
                elif 'appassthru' in flash_method:
                    if provided_programmer and 'serial' in provided_programmer.lower():
                         resolved_programmer = ('' if provided_programmer.lower().startswith('stm32 ') else 'stm32 ') + provided_programmer
                    else: resolved_programmer = 'stm32 appassthru'
                else: resolved_programmer = 'stm32 stlink'
            elif 'esp' in chipset:
                if 'appassthru' in flash_method:
                    if provided_programmer and 'serial' in provided_programmer.lower():
                         resolved_programmer = ('' if (provided_programmer.lower().startswith(chipset) or provided_programmer.lower().startswith('esp')) else f'{chipset} ') + provided_programmer
                    else: resolved_programmer = f'{chipset} appassthru'
                else: resolved_programmer = chipset
            
            if resolved_programmer:
                programmer = resolved_programmer
                json_log(f'Resolved programmer to: {programmer}')

    serialx_no = None
    f = re.search(r' serial([0-9]+?)', programmer.lower())
    if f: serialx_no = int(f.group(1))

    if 'wireless' in (flash_method or '') or 'wirelessbridge' in programmer.lower():
        programmer = 'esp wirelessbridge'
        found_chipset = None
        found_baud = None
        
        best_key = None
        best_key_len = 0
        for key in mlrs_md.g_targetDict.keys():
            if key in filename and len(key) > best_key_len:
                best_key = key
                best_key_len = len(key)
        
        if best_key:
            val = mlrs_md.g_targetDict[best_key]
            if isinstance(val, dict):
                if 'wireless' in val:
                    found_chipset = val['wireless'].get('chipset')
                    found_baud = val['wireless'].get('baud')
                    if 'reset' in val['wireless']: extra_args['reset'] = val['wireless']['reset']
                    if 'erase' in val['wireless']: extra_args['erase'] = val['wireless']['erase']

                best_match = None
                best_match_len = 0
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, dict) and sub_key in filename:
                        if len(sub_key) > best_match_len:
                            best_match = (sub_key, sub_val)
                            best_match_len = len(sub_key)
                
                if best_match:
                    _, sub_val = best_match
                    if 'wireless' in sub_val:
                        found_chipset = sub_val['wireless'].get('chipset')
                        found_baud = sub_val['wireless'].get('baud')
                        if 'reset' in sub_val['wireless']: extra_args['reset'] = sub_val['wireless']['reset']
                        if 'erase' in sub_val['wireless']: extra_args['erase'] = sub_val['wireless']['erase']
        
        if found_chipset:
            if 'esp32c3' in found_chipset: filename = 'mlrs-wireless-bridge-esp32c3.ino.bin'
            elif any(x in found_chipset for x in ['esp8266', 'esp8285', 'esp8255']): filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
            else:
                json_error(f'Unsupported wireless bridge chipset: {found_chipset}')
                return
            
            url = WIRELESSBRIDGE_PATH_URL + filename
            programmer = found_chipset
            json_log(f'Resolved wireless bridge firmware: {filename}')
            if found_baud:
                args.baudrate = found_baud
                json_log(f'Set baudrate to {args.baudrate}')
        else:
            json_log('Warning: Could not resolve wireless bridge chipset, defaulting to esp8266')
            programmer = 'esp8266'
            filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
            url = WIRELESSBRIDGE_PATH_URL + filename

    comport = args.port
    baudrate = args.baudrate

    if 'appassthru' in programmer.lower():
        if serialx_no is None:
            json_error('ArduPilot passthrough requires a serial port number (e.g. serial2)')
            return
        json_log(f'Initializing ArduPilot passthrough on SERIAL{serialx_no}...')
        try:
            init_baud = baudrate if baudrate > 0 else 57600
            options = ['nosysboot', 'scripting'] if 'esp' in programmer.lower() else []
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
            is_bridge = 'wirelessbridge' in (flash_method or '').lower() or 'wirelessbridge' in (provided_programmer or '').lower()
            if baudrate <= 0:
                baudrate = 115200 if is_bridge else 921600
            comport = radio.open_passthrough(comport=comport, baudrate=baudrate, wirelessbridge=is_bridge)
            json_log(f'Passthrough established on {comport}')
        except Exception as e:
            json_error(f'Failed to open EdgeTX passthrough: {e}')
            return

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
        
        success = False
        if 'stm32' in programmer.lower():
            success = flash_stm32(programmer, filepath, comport, baudrate)
        elif 'esp' in programmer.lower():
            success = flash_esp(programmer, filepath, comport, baudrate, extra_args)
        else:
            json_error(f'Unknown programmer: {programmer}')
            return
            
        if success:
            json_progress(100, 'Complete')
            json_success('Flash operation completed!')
        else:
            sys.exit(1)
            
    finally:
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except Exception: pass


# download lua scripts
def cmd_download_lua(args):
    json_log('Downloading Lua scripts...')
    version = args.version
    
    if version == 'main':
        git_url = MAIN_BRANCH_URL
    else:
        versions_res = request_json_dict(FIRMWARE_JSON_URL, '', '')
        if not versions_res:
            json_error('Failed to get versions')
            return

        base_version = version.split('-@')[0] if '-@' in version else version
        if base_version in versions_res:
            git_url = REPOSITORY_URL + versions_res[base_version].get('commit', '')
        else:
            json_error(f'Version {version} not found')
            return
    
    tree_res = request_json_dict(git_url, '?recursive=true', '')
    if not tree_res:
        json_error('Failed to get file tree')
        return
    
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
        json_error(f'File {target_filename} not found' if target_filename else 'No Lua scripts found')
    else:
        json_success(f'Downloaded {downloaded_count} script(s) to {output_dir}')
