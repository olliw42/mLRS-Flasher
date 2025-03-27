#!/usr/bin/env python
#************************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
# OlliW @ www.olliw.eu
#************************************************************
# mLRS Flasher Desktop App
# 27. Mar. 2025 003
#************************************************************
app_version = '27.03.2025-003'

import os, sys, time
import subprocess
import re

from PIL import Image, ImageTk
import customtkinter as ctk
from customtkinter import ThemeManager, filedialog
import configparser

import requests
import json
import base64
import serial
import copy

import assets.mLRS_metadata as mlrs_md


ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
#ctk.set_default_color_theme("green")
#ctk.set_default_color_theme("dark-blue")


def make_dir(path): # os dependent
    if os.name == 'posix':
        os.system('mkdir -p '+path)
    else:
        os.system('md "'+path+'"')

def create_dir(path):
    if not os.path.exists(path):
        make_dir(path)

# used by flashXXX functions to call flasher
def os_system(arg, allow_neg_res=False, pause=True):
    res = os.system(arg)
    if res > 0 or (not allow_neg_res and res < 0):
        print('# ERROR (errno =',res,') DONE #')
        if pause: os.system("pause")
        #sys.exit(1) # no, we don't need to exit
    return res

def os_system_run_as_bat():
    #return False
    if os.name == 'posix': return False
    return True

def os_system_is_frozen_app():
    #return False
    return getattr(sys, 'frozen', False)

def find_serial_ports():
    try:
        from serial.tools.list_ports import comports
        portList = list(comports())
    except:
        print('ERROR: find_serial_ports() [1]')
        return None
    deviceportList = []
    for port in portList:
        #print('*',port.device, port.name, port.description)
        #print(' ',port.hwid, port.vid, port.pid)
        #print(' ',port.manufacturer, port.location, port.product, port.interface)
        deviceportList.append(port.device)
    return deviceportList


import apInitPassthru as appassthru
import edgetxInitPassthru as radio


'''
--------------------------------------------------
STM32 Flashing Tools
--------------------------------------------------
'''

def flash_stm32cubeprogrammer_argstr(programmer, firmware, comport, baudrate):
    if 'dfu' in programmer:
        args = '-c port=usb1 -w "'+firmware+'" -v -g'
    elif 'uart' in programmer:
        args = ' -c port="'+comport+'" br='+str(baudrate)+' -w "' + firmware +'" -v -g'
    else:
        args = '-c port=SWD freq=3900 -w "'+firmware+'" -v -g'
    return args


def flash_stm32cubeprogrammer_win(programmer, firmware):
    ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','win','bin','STM32_Programmer_CLI.exe')
    args = flash_stm32cubeprogrammer_argstr(programmer, firmware)
    #temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    F = open(os.path.join('mlrs_flasher_runner.bat'), 'w')
    F.write(ST_Programmer + ' ' + args +'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** DONE ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO Cheers, and have fun.'+'\n')
###    F.write('@pause'+'\n')
    if os_system_is_frozen_app(): F.write('@pause'+'\n')
    F.close()
    os_system('mlrs_flasher_runner.bat', pause=False)


def flash_stm32cubeprogrammer(programmer, firmware, comport, baudrate):
    if sys.platform.lower() == 'darwin':
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','mac','bin','STM32_Programmer_CLI')
    elif sys.platform.lower() == 'linux':
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','linux','bin','STM32_Programmer_CLI')
    else:
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','win','bin','STM32_Programmer_CLI.exe')
    args = flash_stm32cubeprogrammer_argstr(programmer, firmware, comport, baudrate)
    os_system(ST_Programmer + ' ' + args)


def flash_stm32cubeprogrammer_appassthru_win(serialx_no, firmware):
    ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','win','bin','STM32_Programmer_CLI.exe')
    F = open(os.path.join('mlrs_flasher_runner.bat'), 'w')
    F.write('@apInitPassthru.py -findport'+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@if %ERRORLEVEL% LEQ 0 set /a PORT=-%ERRORLEVEL%'+'\n')
    F.write('@apInitPassthru.py -findbaud -c "COM%PORT%" -s '+str(serialx_no)+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@if %ERRORLEVEL% LEQ 0 set /a BAUDRATE=-%ERRORLEVEL%'+'\n')
    F.write('@apInitPassthru.py -c "COM%PORT%" -s '+str(serialx_no)+' -b %BAUDRATE%'+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@timeout /t 5 /nobreak'+'\n')
    F.write(ST_Programmer + ' -c port="COM%PORT%" br=%BAUDRATE% -w "' + firmware +'" -v -g\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** DONE ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO Cheers, and have fun.'+'\n')
    if os_system_is_frozen_app(): F.write('@pause'+'\n')
    F.close()
    os_system('mlrs_flasher_runner.bat', allow_neg_res=True, pause=False)


def flash_stm32cubeprogrammer_appassthru(serialx_no, firmware):
    comport, baudrate = appassthru.mlrs_open_passthrough(None, 57600, serialx_no)
    #TODO: add a way to gracefully jump out in case of an error
    #print('waiting for 5 secs...')
    time.sleep(5.0)
    flash_stm32cubeprogrammer('uart', firmware, comport, baudrate)


def flashSTM32CubeProgrammer(programmer, firmware):
    #print('flashSTM32CubeProgrammer()',programmer)
    serialx_no = None
    f = re.search(r' serial([0-9]+?)', programmer.lower())
    if f:
        serialx_no = f.group(1)

    if os_system_run_as_bat():
        print('Run on Windows as batch file')
        if 'appassthru' in programmer:
            flash_stm32cubeprogrammer_appassthru_win(serialx_no, firmware)
        else:
            flash_stm32cubeprogrammer_win(programmer, firmware)
        return

    if 'appassthru' in programmer:
        flash_stm32cubeprogrammer_appassthru(serialx_no, firmware)
    else:
        flash_stm32cubeprogrammer(programmer, firmware)
    print()
    print('*** DONE ***')
    print()
    print('Cheers, and have fun.')


#flashSTM32CubeProgrammer('stm32 stlink', 'temp/rx-R9MX-l433cb-v1.3.05-@28fe6be0.hex')
#flashSTM32CubeProgrammer('stm32 appassthru serial2', 'temp/rx-R9MX-l433cb-v1.3.05-@28fe6be0.hex')
#exit(1)


'''
--------------------------------------------------
ESP32/ESP82XX Flashing Tools
--------------------------------------------------
'''

# RadioMaster Bandit, BetaFPV1WMicro seem to use a CP210x usb-ttl adapter
def find_serial_ports_esp_tx_devices():
    try:
        from serial.tools.list_ports import comports
        portList = list(comports())
    except:
        print('ERROR: find_serial_ports_esp_tx_devices() [1]')
        return None
    deviceportList = []
    for port in portList:
        if not 'USB' in port.hwid.upper():
            continue
        if port.vid == 0x0483 and port.pid == 0x374E: # this is STLink
            continue
        if port.vid == 0x0483 and port.pid == 0x5740: # this is EdgeTx/OpenTx
            continue
        if port.vid == 0x1209 and port.pid == 0x5740: # this is ArduPilot
            continue
        if 'CP210' not in port.description: # was 'Silicon Labs CP210x', gave issues on nix
            continue
        deviceportList.append(port.device)
    return deviceportList


def find_serial_ports_usbttl_devices():
    try:
        from serial.tools.list_ports import comports
        portList = list(comports())
    except:
        print('ERROR: find_serial_ports_usbttl_devices() [1]')
        return None
    deviceportList = []
    for port in portList:
        if not 'USB' in port.hwid.upper():
            continue
        if port.vid == 0x0483 and port.pid == 0x374E: # this is STLink
            continue
        if port.vid == 0x0483 and port.pid == 0x5740: # this is EdgeTx/OpenTx
            continue
        if port.vid == 0x1209 and port.pid == 0x5740: # this is ArduPilot
            continue
        deviceportList.append(port.device)
    return deviceportList


def flash_esptool_argstr(programmer, firmware, comport, baudrate):
    assets_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets')
    if 'esp32c3' in programmer: # must come before we test for 'eps32'!
        args = (
            '--chip esp32c3 ' +
            '--port "' + comport + '" ' +
            '--baud ' + str(baudrate) + ' ' +
            '--before default_reset --after hard_reset ' +
            'write_flash ' +
            '-z ' +
            '--flash_mode dio --flash_freq 40m --flash_size 4MB ' +
            '0x0000 ' +
            '"' + os.path.join(assets_path,'esp32c3','bootloader.bin') + '" ' +
            '0x8000 ' +
            '"' + os.path.join(assets_path,'esp32c3','partitions.bin') + '" ' +
            '0xe000 ' +
            '"' + os.path.join(assets_path,'esp32c3','boot_app0.bin') + '" ' +
            '0x10000 ' +
            '"' + firmware + '"'
            )
    elif 'esp32' in programmer:
        args = (
            '--chip esp32 ' +
            '--port "' + comport + '" ' +
            '--baud ' + str(baudrate) + ' ' +
            '--before default_reset --after hard_reset ' +
            'write_flash ' +
            '-z ' +
            '--flash_mode dio --flash_freq 40m --flash_size 4MB ' +
            '0x1000  ' +
            '"' + os.path.join(assets_path,'esp32','bootloader.bin') + '" ' +
            '0x8000 ' +
            '"' + os.path.join(assets_path,'esp32','partitions.bin') + '" ' +
            '0xe000 ' +
            '"' + os.path.join(assets_path,'esp32','boot_app0.bin') + '" ' +
            '0x10000 ' +
            '"' + firmware + '"'
            )
    elif ('esp8266' in programmer or 'esp8285' in programmer) and 'no dtr' in programmer:
        args = (
            '--chip esp8266 ' +
            '--port "' + comport + '" ' +
            '--baud ' + str(baudrate) + ' ' +
            '--before no_reset --after soft_reset ' +
            'write_flash ' +
            '0x0 ' +
            '"' + firmware + '"'
            )
    elif ('esp8266' in programmer or 'esp8285' in programmer): # 'dtr'
        args = (
            '--chip esp8266 ' +
            '--port "' + comport + '" ' +
            '--baud ' + str(baudrate) + ' ' +
            '--before default_reset --after hard_reset ' +
            'write_flash ' +
            '0x0 ' +
            '"' + firmware + '"'
            )
    #print(args)
    #args = '--port "' + radioport + '" ' + '--baud ' + str(baudrate) + ' ' + 'flash_id'
    return args


def flash_esptool_win(programmer, firmware, comport, baudrate):
    esptool_args = flash_esptool_argstr(programmer, firmware, comport, baudrate)

    F = open(os.path.join('mlrs_flasher_runner.bat'), 'w')
    F.write('@'+os.path.join('thirdparty','esptool','esptool.py') + ' ' + esptool_args + '\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** DONE ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO Cheers, and have fun.'+'\n')
###    F.write('@pause'+'\n')
    if os_system_is_frozen_app(): F.write('@pause'+'\n')
    F.close()
    os_system('mlrs_flasher_runner.bat', pause=False)


def flash_esptool(programmer, firmware, comport, baudrate):
    esptool_args = flash_esptool_argstr(programmer, firmware, comport, baudrate)
    #args = '--port "' + radioport + '" ' + '--baud ' + str(baudrate) + ' ' + 'flash_id'

    # TODO: can we catch if this was succesful?
    os_system(os.path.join('thirdparty','esptool','esptool.py') + ' ' + esptool_args)


def flash_esptool_appassthru_win(programmer, serialx_no, firmware):
    F = open(os.path.join('mlrs_flasher_runner.bat'), 'w')
    F.write('@apInitPassthru.py -findport'+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@if %ERRORLEVEL% LEQ 0 set /a PORT=-%ERRORLEVEL%'+'\n')
    F.write('@apInitPassthru.py -findbaud -c "COM%PORT%" -s '+str(serialx_no)+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@if %ERRORLEVEL% LEQ 0 set /a BAUDRATE=-%ERRORLEVEL%'+'\n')
    F.write('@apInitPassthru.py -c "COM%PORT%" -s '+str(serialx_no)+' -b %BAUDRATE% -nosysboot -scripting'+'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@timeout /t 5 /nobreak'+'\n')
    esptool_args = flash_esptool_argstr(programmer, firmware, 'COM%PORT%', '%BAUDRATE%')
    F.write('@'+os.path.join('thirdparty','esptool','esptool.py') + ' ' + esptool_args + '\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** DONE ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO Cheers, and have fun.'+'\n')
    if os_system_is_frozen_app(): F.write('@pause'+'\n')
    F.close()
    os_system('mlrs_flasher_runner.bat', allow_neg_res=True, pause=False)


def flash_esptool_appassthru(programmer, serialx_no, firmware):
    comport, baudrate = appassthru.mlrs_open_passthrough(None, 57600, serialx_no, ['nosysboot', 'scripting'])
    #TODO: add a way to gracefully jump out in case of an error
    #print('waiting for 5 secs...')
    time.sleep(5.0)
    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    flash_esptool(programmer, os.path.join(temp_path, firmware), comport, baudrate)


def flashEspToolProgrammer(programmer, firmware, comport, baudrate):
    serialx_no = None
    f = re.search(r' serial([0-9]+?)', programmer.lower())
    if f:
        serialx_no = f.group(1)

    if os_system_run_as_bat():
        print('Run on Windows as batch file')
        if 'appassthru' in programmer:
            flash_esptool_appassthru_win(programmer, serialx_no, firmware)
        else:
            flash_esptool_win(programmer, firmware, comport, baudrate)
        return

    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    if 'appassthru' in programmer:
        flash_esptool_appassthru(programmer, serialx_no, os.path.join(temp_path, firmware))
    else:
        flash_esptool(programmer, os.path.join(temp_path, firmware), comport, baudrate)
    print()
    print('*** DONE ***')
    print()
    print('Please remove the USB cable.')
    print('Cheers, and have fun.')


#os_system('mlrs_flasher_runner.bat', allow_neg_res=True, pause=False)
#exit(1)
#flashEspToolProgrammer('esp8285 appassthru serial2', 'temp/rx-bayck-nano-pro-900-v1.3.05-@28fe6be0.bin', None, None)
#exit(1)


'''
--------------------------------------------------
Internal Tx Module Flashing Tools
--------------------------------------------------
'''

def flash_internal_elrs_tx_module_win(firmware, wirelessbridge=False):
    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    if wirelessbridge:
        baudrate = 115200
        passthru_args = '-b '+str(baudrate)+' --wirelessbridge'
        esptool_args = flash_esptool_argstr('esp8266', os.path.join(temp_path, firmware), 'COM%RADIOPORT%', baudrate)
    else:
        baudrate = 921600
        passthru_args = '-b '+str(baudrate)
        esptool_args = flash_esptool_argstr('esp32', os.path.join(temp_path, firmware), 'COM%RADIOPORT%', baudrate)
    F = open(os.path.join('mlrs_flasher_runner.bat'), 'w')
    F.write('@edgetxInitPassthru.py ' + passthru_args +'\n')
    F.write('@if %ERRORLEVEL% GEQ 1 EXIT /B 1'+'\n')
    F.write('@if %ERRORLEVEL% LEQ 0 set /a RADIOPORT=-%ERRORLEVEL%'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** 3. Flashing the internal Tx Module ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO The firmware to flash is: '+firmware+'\n')
    F.write('@'+os.path.join('thirdparty','esptool','esptool.py') + ' ' + esptool_args +'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO *** DONE ***'+'\n')
    F.write('@ECHO.'+'\n')
    F.write('@ECHO Please remove the USB cable.'+'\n')
    F.write('@ECHO Cheers, and have fun.'+'\n')
###    F.write('@pause'+'\n')
    if os_system_is_frozen_app(): F.write('@pause'+'\n')
    F.close()
    os_system('mlrs_flasher_runner.bat', pause=False)

#flash_internal_elrs_tx_module_win('tx-jumper-internal-900-v1.3.05-@28fe6be0.bin')
#exit(1)


def flashInternalElrsTxModule(programmer, firmware):
    if os_system_run_as_bat():
        print('Run on Windows as batch file')
        flash_internal_elrs_tx_module_win(firmware, wirelessbridge = False)
        return

    # firmware filename gives the complete path
    #print(filename)
    #print(programmer)
    baudrate = 921600
    radioport = radio.open_passthrough(baudrate)

    print()
    print('*** 3. Flashing the internal Tx Module ***')
    print()
    print('The firmware to flash is:', firmware)

    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    # TODO: can we catch if this was succesfull?
    flash_esptool('esp32', os.path.join(temp_path, firmware), radioport, baudrate)

    print()
    print('*** DONE ***')
    print()
    print('Please remove the USB cable.')
    print('Cheers, and have fun.')


def flashInternalElrsTxModuleWirelessBridge(programmer, firmware):
    if os_system_run_as_bat():
        print('Run on Windows as batch file')
        flash_internal_elrs_tx_module_win(firmware, wirelessbridge = True)
        return

    #print(programmer)
    baudrate = 115200
    radioport = radio.open_passthrough(baudrate, wirelessbridge = True)

    print()
    print('*** 3. Flashing the wireless bridge of the internal Tx Module ***')
    print()
    print('The firmware to flash is:', firmware)

    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')
    # TODO: can we catch if this was succesfull?
    flash_esptool('esp8266', os.path.join(temp_path,firmware), radioport, baudrate)

    print()
    print('*** DONE ***')
    print()
    print('Please remove the USB cable.')
    print('Cheers, and have fun.')


'''
--------------------------------------------------
API Helper
--------------------------------------------------
'''

g_TxModuleExternal_minimal_version = 'v1.3.00'
g_Receiver_minimal_version = 'v1.3.00'
g_TxModuleInternal_minimal_version = 'v1.3.05'
g_LuaScript_minimal_version = 'v1.3.00'

# url to file mlrs_firmware_urls.json, which hosts info on releases
g_firmware_json_url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/tools/web/mlrs_firmware_urls.json'
# url to a release branch
g_repository_url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/'
# url to main branch
g_main_branch_url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/main'

# cache for github downloads
g_jsonCacheDict = {}

def requestJsonDict(url, extension='', error_msg=''):
    if url in g_jsonCacheDict.keys():
        print('* cached', url)
        return copy.deepcopy(g_jsonCacheDict[url])
    print('* request', url)
    res = None
    tries = 4
    while tries > 0:
        try:
            res = requests.get(url + extension, allow_redirects=True, timeout=(2,4))
            if b'API rate limit exceeded' in res.content:
                print(res.content)
                print('DONWLOAD FAILED!')
                print(error_msg)
                return False
            jsonDict = res.json()
            break # got it
        except:
            tries = tries - 1
            if tries < 0:
                if res: print(res.content)
                print(error_msg)
                return None
    
    g_jsonCacheDict[url] = copy.deepcopy(jsonDict)
    return jsonDict


def requestData(url, error_msg=''):
    print('* request', url)
    jsonDict = None
    tries = 4
    while tries > 0:
        try:
            res = requests.get(url, allow_redirects=True, timeout=(2,4))
            if b'API rate limit exceeded' in res.content:
                print(res.content)
                print('DONWLOAD FAILED!')
                print(error_msg)
                return False
            try:
                jsonDict = res.json()
            except:
                data = res.content
            break # got it    
        except:
            tries = tries - 1
            if tries < 0:
                print(res.content)
                print(error_msg)
                return None
    if jsonDict:
        if jsonDict['encoding'] == 'base64':
            data = base64.b64decode(jsonDict['content'])
        else:
            data = jsonDict['content']
    return data


# API for app
def downloadVersionsDict():
    # download mlrs_firmware_urls.json
    # it holds the "released" versions, i.e., all non-dev versions
    # url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/tools/web/mlrs_firmware_urls.json'
    res = requestJsonDict(g_firmware_json_url, '', 'ERROR: downloadVersionsDict() [1]')
    if not res:
        return res
    resDict = res
    #print(resDict)

    # manipulate resDict: add fields versionStr and gitUrl
    for key in list(resDict.keys()):
        v = key.split('.')
        patch = int(v[2])
        if patch == 0: # .00
            resDict[key]['versionStr'] = key + ' (release)'
        elif patch & 1 == 0: # even
            resDict[key]['versionStr'] = key + ' (pre-release)'
        elif patch & 1 > 0: # odd
            resDict[key]['versionStr'] = key + ' (dev)'
        else:
            resDict[key]['versionStr'] = key + ' (?)' # should not happen, play it safe

        # url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/' + resDict[key]['commit'] + '?recursive=true'
        resDict[key]['gitUrl'] = g_repository_url + resDict[key]['commit']

    # Figure out also the pre-release dev version. This needs work:
    # We need to read the main json, to get the current firmware folder url,
    # then read one file name in this folder, and extract the version part from the file name.
    # url = 'https://api.github.com/repos/olliw42/mLRS/git/trees/main'
    res = requestJsonDict(g_main_branch_url, '', 'ERROR: downloadVersionsDict() [2]')
    if not res:
        return res
    resMainList = res['tree'] # it's a list of dictionaries
    #print(resMainList)

    firmwarePathDict = None
    for key in resMainList:
        if key['path'] == 'firmware':
            firmwarePathDict = key
            break
    if firmwarePathDict == None: # something is wrong, so go ahead with what we have
        return resDict
    #print(firmwarePathDict)

    url_main_firmware = firmwarePathDict['url'] # not so many, so we can afford getting them all
    res = requestJsonDict(url_main_firmware, '?recursive=true', 'ERROR: downloadVersionsDict() [3]')
    if not res:
        return res
    resMainFirmwareList = res['tree'] # it's a list of dictionaries
    #print(resMainFirmwareList)

    # firmware_filename looks like pre-release-stm32/rx-E77-MBLKit-wle5cc-400-tcxo-v1.3.01-@ae667b78.hex
    # find one file with a -@ in the name, and asumme it is representative for all dev versions
    # this means in all firmware/ subfolders only equal -@ must appear
    # regex to get version and commit
    for key in resMainFirmwareList:
        if '-@' in key['path']: # this is one
            #print('we got one')
            #print(key)
            #print(key['path'])
            f = re.search(r'-(v\d\.\d+?\.\d+?-@[A-Za-z0-9]+?)\.', key['path']) # TODO: doesn't correctly parse branch dev versions
            #print(f, f.group(1))
            if f:
                resDict[f.group(1)] = {
                    'versionStr' : f.group(1) + ' (dev)',
                    'gitUrl' : url_main_firmware # ??? ok ???
                }
            break

    #print(resDict)
    return resDict


# API for app
# Get files list from github repo, for a specifc tree, and filter according to what we want.
# pass in a GitHub tree URL like https://api.github.com/repos/olliw42/mLRS/git/trees/f12d680?recursive=true
# this is needed to get the list of files from the location which is specific to the version
def downloadFilesListFromTree(txrxlua, url, device='', version=''):
    res = requestJsonDict(url, '?recursive=true', 'ERROR: downloadFilesListFromTree() [1]')
    if not res:
        return None
    resList = res['tree'] # it's a list of dictionaries
    if txrxlua == 'lua': # 'lua'
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            if 'lua/' not in key['path']:
                resList.remove(key)
            elif key['type'] != 'blob': # seems to not be needed, as all 'lua/' seem to be blob
                resList.remove(key)
            elif '.lua' not in key['path']: # only accept files with '.lua' extension
                resList.remove(key)
    elif txrxlua == 'txint': # 'tx int'
        if device == '' or version == '': print('ERROR: downloadFilesListFromTree() [2]')
        #print(url, device, version)
        #print(resList)
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            #if 'firmware/' not in key['path']:
            #    resList.remove(key)
            if key['type'] != 'blob':
                resList.remove(key)
            elif '-stm32' in key['path']: # remove all files with '-stm32'
                resList.remove(key)
            elif '-esp' not in key['path']: # only accept files with '-esp', should be redundant
                resList.remove(key)
            elif '-internal-' not in key['path']:
                resList.remove(key)
            elif version not in key['path']: # ensure we only have the desired firmware version
                resList.remove(key)
            elif device not in key['path']: # only accept tx-device-internal
                resList.remove(key)
    else: # 'tx' or 'rx'
        if device == '' or version == '': print('ERROR: downloadFilesListFromTree() [3]')
        #print(url, device, version)
        #print(resList)
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            #if 'firmware/' not in key['path']:
            #    resList.remove(key)
            if key['type'] != 'blob': # seems to not be needed, as all 'firmware/' seem to be blob
                resList.remove(key)
            #elif '-esp' in key['path']: # remove all files with '-esp'
            #    resList.remove(key)
            #elif '-stm32' not in key['path']: # only accept files with '-stm32', should be redundant
            #    resList.remove(key)
            elif '-internal-' in key['path']:
                resList.remove(key)
            elif '-stm32' not in key['path'] and '-esp' not in key['path']: # only accept files with '-stm32' or '-esp'
                resList.remove(key)
            elif version not in key['path']: # ensure we only have the desired firmware version
                resList.remove(key)
            elif device not in key['path']: # only accept tx-device-xxx or rx-device-xxx
                resList.remove(key)

    ''' import pprint
    F = open('filesfromtree-'+txorrxortxintorlua+'.txt', 'w')
    F.write(url)
    F.write('\n\r')
    F.write( pprint.pformat(resList) )
    F.close() '''

    return resList


def downloadFileAndWriteToDisk(url, filename):
    #url = 'https://api.github.com/repos/olliw42/mLRS/git/blobs/9cfb92d2de3f0582b6b33279abecd941885681d4'
    #filename = 'rx-matek-mr24-30-g431kb-can-v1.3.04.hex'
    data = requestData(url, 'ERROR: downloadFileAndWriteToDisk()')
    F = open(filename, 'wb')
    F.write(data)
    F.close()
    return True


# API for app
def flashDevice(programmer, url, filename, comport=None, baudrate=None):
    #print('flashDevice()',programmer)
    #print(url)
    #print(filename)
    create_dir('temp')
    res = downloadFileAndWriteToDisk(url, os.path.join('temp',filename))
    if not res:
        print('ERROR: flashDevice() [1]')
        return
    #print(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'temp',filename)
    #print(filepath)
    if 'wirelessbridge' in programmer:
        # handle WirelessBridge
        if 'internal' in programmer:
            if ('esp8266' in programmer or 'esp8285' in programmer):
                flashInternalElrsTxModuleWirelessBridge(programmer, filepath)
                return
        else:
            if ('esp8266' in programmer or 'esp8285' in programmer):
                flashEspToolProgrammer(programmer, filepath, comport, baudrate)
                return
    elif 'stm32' in programmer:
        # STM32
        flashSTM32CubeProgrammer(programmer, filepath)
        return
    elif 'esp' in programmer: # 'esp32'
        # ESP
        if 'internal' in programmer:
            flashInternalElrsTxModule(programmer, filepath)
            return
        else:
            flashEspToolProgrammer(programmer, filepath, comport, baudrate)
            return
    print('ERROR: flashDevice() [2]')


'''
--------------------------------------------------
Miscellaneous utils
--------------------------------------------------
'''

def version_str_to_int(v_str):
    if v_str[0] != 'v':
        return 0
    return int(v_str[1]+'0'+v_str[3]+v_str[5:7])


'''
--------------------------------------------------
CustomTKInter App
--------------------------------------------------
'''

class CTkCompPortOptionMenu(ctk.CTkOptionMenu):
    def __init__(self, master, porttype='default', **kwargs):
        super().__init__(master=master, **kwargs)
        self.porttype = porttype

    def update(self):
        sel = self.get()
        if 'esp' in self.porttype and 'tx' in self.porttype:
            portlist = find_serial_ports_esp_tx_devices()
        elif 'usbttl' in self.porttype:
            portlist = find_serial_ports_usbttl_devices()
        else:
            portlist = find_serial_ports()
        if not portlist:
            portlist = ['COM1']
        #print(portlist)
        self.configure(values=portlist, require_redraw=True)
        if sel in portlist:
            self.set(sel)
        else:
            self.set(portlist[0])

    def _open_dropdown_menu(self):
        self.update()
        super()._open_dropdown_menu()


class CTkFlashButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master=master, **kwargs)
        super().configure(fg_color="green", hover_color="#006400")


class CTkInfoTextbox(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        super().__init__(master=master, **kwargs)
        super().delete("0.0", "end")
        super().configure(state="disabled")
        super().tag_config('warning', foreground='red')

    def setText(self, txt, tag=None):
        super().configure(state="normal")
        super().delete("0.0", "end")
        super().insert("0.0", txt)
        if tag:
            super().tag_add(tag[0], tag[1], tag[2])
        super().configure(state="disabled")
        

warning_dev_version = (
    "WARNING: You are about to flash a 'dev' firmware version.\n" + 
    "Please ensure you understand the risks involved with this.\n\n"
    )
warning_dev_version_tag = ['warning','1.0','2.100']


class App(ctk.CTk):

    #--------------------------------------------------
    #-- Interface to low level handler
    #--------------------------------------------------

    # needs to be called only once at startup
    # calls getDevicesDict(), and updates the 'Device Type' widgets accordingly
    def updateDeviceTypes(self):
        self.txDeviceTypeDict = mlrs_md.g_txModuleExternalDeviceTypeDict
        keys = list(self.txDeviceTypeDict.keys())
        self.fTxModuleExternal_DeviceType_menu.configure(values=keys)
        self.fTxModuleExternal_DeviceType_menu.set(keys[0]) # this is needed to make the menu update itself

        self.rxDeviceTypeDict = mlrs_md.g_receiverDeviceTypeDict
        keys = list(self.rxDeviceTypeDict.keys())
        self.fReceiver_DeviceType_menu.configure(values=keys)
        self.fReceiver_DeviceType_menu.set(keys[0])

        self.txIntDeviceTypeDict = mlrs_md.g_txModuleInternalDeviceTypeDict
        keys = list(self.txIntDeviceTypeDict.keys())
        self.fTxModuleInternal_DeviceType_menu.configure(values=keys)
        self.fTxModuleInternal_DeviceType_menu.set(keys[0])

    # needs to be called only once at startup
    # calls downloadVersionsDict(), and updates the Firmware Version' widgets accordingly
    def updateFirmwareVersions(self):
        self.firmwareVersionDict = downloadVersionsDict()
        if self.firmwareVersionDict:
            keys = []
            for key in list(self.firmwareVersionDict.keys()): # we assume here it cannot be empty
                keys.append(self.firmwareVersionDict[key]['versionStr'])
        else:
            self.firmwareVersionDict = None
            keys = ['download failed...']
            # TODO: raise window
        txkeys = []; rxkeys = []; txintkeys = []; luakeys = []
        if 'failed' in keys[0]:
            txkeys = keys; rxkeys = keys; txintkeys = keys; luakeys = keys
        else:
            for key in keys:
                v = version_str_to_int(key)
                if v >= version_str_to_int(g_TxModuleExternal_minimal_version): txkeys.append(key)
                if v >= version_str_to_int(g_Receiver_minimal_version): rxkeys.append(key)
                if v >= version_str_to_int(g_TxModuleInternal_minimal_version): txintkeys.append(key)
                if v >= version_str_to_int(g_LuaScript_minimal_version): luakeys.append(key)
        self.fTxModuleExternal_FirmwareVersion_menu.configure(values=txkeys)
        self.fTxModuleExternal_FirmwareVersion_menu.set(txkeys[0]) # this is needed to make the menu update itself
        self.fReceiver_FirmwareVersion_menu.configure(values=rxkeys)
        self.fReceiver_FirmwareVersion_menu.set(rxkeys[0])
        self.fTxModuleInternal_FirmwareVersion_menu.configure(values=txintkeys)
        self.fTxModuleInternal_FirmwareVersion_menu.set(txintkeys[0])
        self.fLuaScript_FirmwareVersion_menu.configure(values=luakeys)
        self.fLuaScript_FirmwareVersion_menu.set(luakeys[0])
        #return self.firmwareVersionDict != None
        return 'failed' not in keys[0]

    # helper
    def _download_firmware_files(self, txrx, device_type, firmware_version):
        if txrx == 'tx':
            if self.txDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.txDeviceTypeDict[device_type]['fname'] # that's the name of the device in the filename
        elif txrx == 'rx':
            if self.rxDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.rxDeviceTypeDict[device_type]['fname'] # that's the name of the device in the filename
        elif txrx == 'txint':
            if self.txIntDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.txIntDeviceTypeDict[device_type]['fname'] # that's the name of the device in the filename
        firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(device_type, device_type_f)
        #print(firmware_version, firmware_version_gitUrl)
        res = downloadFilesListFromTree(txrx, firmware_version_gitUrl, device_type_f, firmware_version)
        if res == None:
            print('ERROR: _download_firmware_files() [1]')
            return ['download failed...']
        if txrx == 'tx':
            self.txFirmwareFilesList = res # must be self as list is needed later also
            firmwareFilesList = self.txFirmwareFilesList
        elif txrx == 'rx':
            self.rxFirmwareFilesList = res # must be self as list is needed later also
            firmwareFilesList = self.rxFirmwareFilesList
        elif txrx == 'txint':
            self.txIntFirmwareFilesList = res # must be self as list is needed later also
            firmwareFilesList = self.txIntFirmwareFilesList
        else:
            print('ERROR: _download_firmware_files() [2]')
            return ['download failed...']
        #print(firmwareFilesList)
        if firmwareFilesList == None:
            return ['download failed...']
        keys = []
        for key in firmwareFilesList:
            fpath, fname = os.path.split(key['path'])
            keys.append(fname)
        if not keys:
            keys.append('not available') # can happen
        #print(keys)
        return keys

    # needs to be called whenever device type or firmware version changes
    # calls _download_firmware_files() to get the 'tx' file names in the tree, and updates TxModuleExternal 'Firmware Files' widget
    def updateTxModuleExternalFirmwareFiles(self):
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        firmware_version = self.fTxModuleExternal_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_firmware_files('tx', device_type, firmware_version)
        self.fTxModuleExternal_FirmwareFile_menu.configure(values=keys)
        self.fTxModuleExternal_FirmwareFile_menu.set(keys[0])
        return 'failed' not in keys[0]

    # needs to be called whenever device type or firmware version changes
    # calls _download_firmware_files() to get the 'rx' file names in the tree, and updates Receiver 'Firmware Files' widget
    def updateReceiverFirmwareFiles(self):
        device_type = self.fReceiver_DeviceType_menu.get()
        firmware_version = self.fReceiver_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_firmware_files('rx', device_type, firmware_version)
        self.fReceiver_FirmwareFile_menu.configure(values=keys)
        self.fReceiver_FirmwareFile_menu.set(keys[0])
        return 'failed' not in keys[0]

    # needs to be called whenever device type or firmware version changes
    # calls _download_firmware_files() to get the 'txint' file names in the tree, and updates TxModuleInternal 'Firmware Files' widget
    def updateTxModuleInternalFirmwareFiles(self):
        device_type = self.fTxModuleInternal_DeviceType_menu.get()
        firmware_version = self.fTxModuleInternal_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_firmware_files('txint', device_type, firmware_version)
        self.fTxModuleInternal_FirmwareFile_menu.configure(values=keys)
        self.fTxModuleInternal_FirmwareFile_menu.set(keys[0])
        return 'failed' not in keys[0]

    # helper
    def _download_luascript_files(self, firmware_version):
        if self.firmwareVersionDict == None:
            return ['download failed...']
        firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(firmware_version, firmware_version_gitUrl)
        self.luaScriptFilesList = downloadFilesListFromTree('lua', firmware_version_gitUrl) # must be self as list is needed later also
        #print(self.luaScriptFilesList)
        if self.luaScriptFilesList == None:
            return ['download failed...']
        keys = []
        for key in self.luaScriptFilesList:
            if 'mLRS.lua' in key['path']: keys.append('color screen (mLRS.lua)')
        for key in self.luaScriptFilesList:
            if 'mLRS-bw.lua' in key['path']: keys.append('bw screen (mLRS-bw.lua)')
        for key in self.luaScriptFilesList:
            if 'mLRS-bw-luac.lua' in key['path']: keys.append('bw screen compiled (mLRS-bw-luac.lua)')
        if not keys:
            keys.append('not available') # can happen
        #print(keys)
        return keys

    # needs to be called whenever device type or firmware version changes
    # calls _download_luascript_files() to get the '.lua' file names in the tree, and updates LuaScript 'Radio Screen Type' widget
    def updateLuaScriptFiles(self):
        firmware_version = self.fLuaScript_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_luascript_files(firmware_version)
        self.fLuaScript_RadioScreen_menu.configure(values=keys)
        self.fLuaScript_RadioScreen_menu.set(keys[0])
        return 'failed' not in keys


    # calls flashDevice() for the selected device, firmware url, and filename, to initiate flashing
    def flashTxModuleExternalFirmware(self):
        #print('flashTxModuleExternalFirmware()')
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleExternal_FirmwareFile_menu.get()
        if 'failed' in firmware_filename:
            print('ERROR: flashTxModuleExternalFirmware() [1]')
            return
        #print(device_type, self.txDeviceTypeDict[device_type])
        #print(firmware_filename)
        chipset, flashmethod, description, wireless = self.get_metadata('tx', device_type, firmware_filename)
        if not flashmethod: flashmethod = 'default' # can be None
        #print(self.txFirmwareFilesList)
        #print(chipset)
        for key in self.txFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                if 'stm32' in chipset:
                    if 'dfu' in flashmethod:
                        flashDevice(chipset + ' dfu', key['url'], firmware_filename)
                    else:
                        flashDevice(chipset + ' stlink', key['url'], firmware_filename)
                    return
                elif 'esp32' in chipset:
                    comport = self.fTxModuleExternal_ComPort_menu.get()
                    print('--->',comport)
                    flashDevice(chipset, key['url'], firmware_filename, comport=comport, baudrate=921600)
                    return
        print('ERROR: flashTxModuleExternalFirmware() [2]')

    def flashTxModuleExternalWirelessBridgeFirmware(self):
        #print('flashTxModuleExternalWirelessBridgeFirmware()')
        comport = self.fTxModuleExternal_ComPort_menu.get()
        #print('--->',comport)
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleExternal_FirmwareFile_menu.get()
        if 'failed' in firmware_filename:
            print('ERROR: flashTxModuleExternalWirelessBridgeFirmware() [1]')
            return
        chipset, flashmethod, description, wireless = self.get_metadata('tx', device_type, firmware_filename)
        #print('--->',wireless)
        programmer = 'wirelessbridge'
        if 'chipset' in wireless:
            programmer = programmer + ' ' + wireless['chipset']
        else:
            programmer = programmer + ' esp8266'
        if 'reset' in wireless:
            programmer = programmer + ' ' + wireless['reset']
        else:
            programmer = programmer + ' dtr'
        if 'baud' in wireless:
            baudrate = wireless['baud']
        else:
            baudrate = 921600
        url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/firmware/wirelessbridge-esp8266/mlrs-wireless-bridge-esp8266.ino.bin'
        firmware_filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
        flashDevice(programmer, url, firmware_filename, comport, baudrate)

    # calls flashDevice() for the selected device, firmware url, and filename, to initiate flashing
    def flashReceiverFirmware(self):
        device_type = self.fReceiver_DeviceType_menu.get()
        firmware_filename = self.fReceiver_FirmwareFile_menu.get()
        if 'failed' in firmware_filename:
            print('ERROR: flashReceiverFirmware() [1]')
            return
        #print(firmware_filename)
        chipset, flashmethod, description, wireless = self.get_metadata('rx', device_type, firmware_filename)
        if not flashmethod: flashmethod = 'default' # can be None
        if ',' in flashmethod: # the target allows several flashmethod, so we need to get the one which is selected
            sel = self.fReceiver_Flashmethod_menu.get()
            flashmethod = self.get_flashmethod_from_menu_opt(sel)
        #print('--->',flashmethod)
        #print(chipset)
        #print(self.rxFirmwareFilesList)
        for key in self.rxFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                if 'stm32' in chipset:
                    if 'dfu' in flashmethod:
                        flashDevice('stm32 dfu', key['url'], firmware_filename)
                    elif 'appassthru' in flashmethod:
                        serialx = self.fReceiver_Serialx_menu.get().lower()
                        flashDevice('stm32 appassthru '+serialx, key['url'], firmware_filename)
                    else:
                        flashDevice('stm32 stlink', key['url'], firmware_filename) # STLink is default
                    return
                elif 'esp' in chipset:
                    # VSCODE/Platformio does 'no dtr', so we do too, seems not be critical
                    # VSCODE/Platformio uses for esp32 --flash_freq 80m, we do --flash_freq 40m
                    if 'appassthru' in flashmethod:
                        serialx = self.fReceiver_Serialx_menu.get().lower()
                        flashDevice(chipset + ' no dtr appassthru ' + serialx, key['url'], firmware_filename)
                    else: # 'esptool'
                        comport = self.fReceiver_ComPort_menu.get()
                        print('--->',comport)
                        flashDevice(chipset + ' no dtr', key['url'], firmware_filename, comport=comport, baudrate=921600)
                    return
        print('ERROR: flashReceiverFirmware() [2]')

    def flashTxModuleInternalFirmware(self):
        device_type = self.fTxModuleInternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleInternal_FirmwareFile_menu.get()
        if 'failed' in firmware_filename:
            print('ERROR: flashTxModuleInternalFirmware() [1]')
            return
        chipset, flashmethod, description, wireless = self.get_metadata('txint', device_type, firmware_filename)
        if chipset != 'esp32': # currently must be esp32
            print('ERROR: flashTxModuleInternalFirmware() [3]')
            sys.exit(1)
        for key in self.txIntFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                flashDevice('esp32 internal', key['url'], firmware_filename)
                return
        print('ERROR: flashTxModuleInternalFirmware() [2]')

    def flashTxModuleInternalWirelessBridgeFirmware(self):
        url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/firmware/wirelessbridge-esp8266/mlrs-wireless-bridge-esp8266.ino.bin'
        firmware_filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
        flashDevice('wirelessbridge internal esp8285', url, firmware_filename)


    # calls downloadFileAndWriteToDisk() for the selected filename, and saves it
    def saveLuaScript(self, filename):
        #print(filename)
        # hä, what was this good for ??
        #if self.firmwareVersionDict == None:
        #    return
        #firmware_version = self.fLuaScript_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        #firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(firmware_version, firmware_version_gitUrl)
        if self.luaScriptFilesList == None:
            print('ERROR: saveLuaScript() [1]')
            return
        #print(self.luaScriptFilesList)
        for key in self.luaScriptFilesList        :
            fpath, fname = os.path.split(key['path'])
            if fname.lower() in filename.lower():
                downloadFileAndWriteToDisk(key['url'], filename)
                return
        print('ERROR: saveLuaScript() [2]')


    #--------------------------------------------------
    #-- Init and Startup
    #--------------------------------------------------

    def __init__(self):
        super().__init__()

        self.title('mLRS Flasher Desktop App '+app_version)
        self.geometry('800x600')
        #self.iconbitmap(os.path.join('assets','mLRS_logo_round.ico')) # does not work on Mac
        self.wm_iconbitmap()
        self.iconphoto(False, ImageTk.PhotoImage(file = os.path.join('assets','mLRS_logo_round.ico')))

        #-- set grid layout 1x2
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        #-- create high level frames
        self.initNavgiationPane()
        self.initTxModuleExternalFrame()
        self.initReceiverFrame()
        self.initTxModuleInternalFrame()
        self.initLuaScriptFrame()

        #-- finalize
        # select default frame
        self.fNavigation_select_frame_by_name('tx_module_ext')

        self.startup()

        self.ini_open()

    def startup(self):
        # these are 'static' and equal for each section
        self.updateDeviceTypes()

    def after_startup(self):
        print('downloading metadata from github repository...')
        res1 = self.updateFirmwareVersions()
        res2 = self.fTxModuleExternal_Startup()
        res3 = self.fReceiver_Startup()
        res4 = self.fTxModuleInternal_Startup()
        res5 = self.fLuaScript_Startup()
        if (res1 and res2 and res3 and res4 and res5): print('... ok')

    def ini_open(self):
        self.ini_config = configparser.ConfigParser()
        found = self.ini_config.read('mLRS_Flasher.ini')
        #print(found)
        if not self.ini_config.has_section('app'): # missing so add with default
            self.ini_config.add_section('app')
            self.ini_config.set('app', 'appearance', self.fNavigation_SetAppearanceMode_menu.get())
        res = self.ini_config.get('app', 'appearance')
        #print(res)
        self.fNavigation_SetAppearanceMode_menu.set(res)
        ctk.set_appearance_mode(self.fNavigation_SetAppearanceMode_menu.get()) # it seems the event loop is not yet running

    def closed(self):
        print('Thanks for using mLRS.')
        self.ini_config.set('app', 'appearance', self.fNavigation_SetAppearanceMode_menu.get())
        try:
            F = open('mLRS_Flasher.ini', 'w')
            self.ini_config.write(F)
            F.close()
        except:
            pass


    #--------------------------------------------------
    #-- Miscellaneous
    #--------------------------------------------------

    def _get_metadata(self, device_type_f, firmware_filename):
        chipset = None
        flashmethod = None
        description = None
        wireless = None
        if device_type_f in mlrs_md.g_targetDict.keys():
            device_type_dict = mlrs_md.g_targetDict[device_type_f]
            if 'chipset' in device_type_dict.keys():
                chipset = device_type_dict['chipset']
            if 'flashmethod' in device_type_dict.keys():
                flashmethod = device_type_dict['flashmethod']
            if 'description' in device_type_dict.keys():
                description = device_type_dict['description']
            if 'wireless' in device_type_dict.keys():
                wireless = device_type_dict['wireless']
            #print("XXXX",device_type_dict)
            #print(firmware_filename)
            if not 'failed' in firmware_filename:
                for key in device_type_dict.keys(): # search for target entry
                    if key in firmware_filename:
                        target_dict = device_type_dict[key]
                        #print("found", target_dict)
                        if 'chipset' in target_dict.keys():
                            chipset = target_dict['chipset']
                        if 'flashmethod' in target_dict.keys():
                            flashmethod = target_dict['flashmethod']
                        if 'description' in target_dict.keys():
                            description = target_dict['description']
                        if 'wireless' in target_dict.keys():
                            wireless = target_dict['wireless']
                        break
        return chipset, flashmethod, description, wireless

    def get_metadata(self, txrx, device_type, firmware_filename):
        if txrx == 'tx':
            device_type_f = self.txDeviceTypeDict[device_type]['fname']
            chipset = self.txDeviceTypeDict[device_type]['chipset']
        elif txrx == 'rx':
            device_type_f = self.rxDeviceTypeDict[device_type]['fname']
            chipset = self.rxDeviceTypeDict[device_type]['chipset']
        elif txrx == 'txint':
            device_type_f = self.txIntDeviceTypeDict[device_type]['fname']
            chipset = self.txIntDeviceTypeDict[device_type]['chipset']
        #print(txrx, device_type_f, chipset)
        chipset2, flashmethod, description, wireless = self._get_metadata(device_type_f, firmware_filename)
        if chipset2:
            chipset = chipset2
        if 'xx' in chipset.lower():
            print("ERROR: Something wrong in get_metadata()")
        return chipset, flashmethod, description, wireless

    def get_flashmethod_list_for_menu(self, flashmethod_str):
        flashmethod_list = flashmethod_str.split(',')
        menu_list = []
        for flashmethod in flashmethod_list:
            if flashmethod == 'dfu': menu_list.append('DFU (USB)')
            if flashmethod == 'stlink': menu_list.append('STLink (SWD)')
            if flashmethod == 'esptool': menu_list.append('ESPTool (UART)')
            if flashmethod == 'appassthru': menu_list.append('AP Passthru')
        if len(menu_list) == 0: menu_list.append('failed')
        return menu_list

    def get_flashmethod_from_menu_opt(self, menu_opt):
        if 'DFU' in menu_opt: return 'dfu'
        if 'STLink' in menu_opt: return 'stlink'
        if 'ESPTool' in menu_opt: return 'esptool'
        if 'AP Passthru' in menu_opt: return 'appassthru'
        return 'default'


    #--------------------------------------------------
    #-- Navigation Pane
    #-- init and handlers
    #--------------------------------------------------

    def initNavgiationPane(self):
        self.fNavigation = ctk.CTkFrame(self, corner_radius=0)
        self.fNavigation.grid(row=0, column=0, sticky="nsew")
        self.fNavigation.grid_rowconfigure(6, weight=1)

        # header logo
        assets_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")

        self.mLRS_Logo_image = ctk.CTkImage(Image.open(os.path.join(assets_path, "mLRS_logo_long_w_slogan_378x194.png")), size=(150, 194/378*170))
        self.fNavigation_Logo_logo = ctk.CTkLabel(self.fNavigation,
            text="", image=self.mLRS_Logo_image)
        self.fNavigation_Logo_logo.grid(row=0, column=0, padx=10, pady=10)

        self.fNavigation_Logo_label = ctk.CTkLabel(self.fNavigation,
            text="mLRS Flasher",
            font=ctk.CTkFont(size=15, weight="bold"))
        self.fNavigation_Logo_label.grid(row=1, column=0, padx=20, pady=10)

        # navigation options

        self.fNavigation_fg_color = ThemeManager.theme["CTkSegmentedButton"]["fg_color"]
        self.fNavigation_hover_color = ThemeManager.theme["CTkSegmentedButton"]["unselected_hover_color"]
        self.fNavigation_selected_color = ThemeManager.theme["CTkSegmentedButton"]["selected_color"]
        self.fNavigation_selected_hover_color = ThemeManager.theme["CTkSegmentedButton"]["selected_hover_color"]
        #print(ThemeManager.theme["CTkSegmentedButton"])

        self.fNavigation_TxModuleExternal_button = ctk.CTkButton(self.fNavigation,
            text="Tx Module (external)",
            corner_radius=0, height=40, border_spacing=10,
            #image=self.home_image,
            #anchor="w",
            command=self.fNavigation_TxModuleExternal_button_event)
        self.fNavigation_TxModuleExternal_button.grid(row=2, column=0, sticky="ew")

        self.fNavigation_Receiver_button = ctk.CTkButton(self.fNavigation,
            text="Receiver",
            corner_radius=0, height=40, border_spacing=10,
            #image=self.chat_image,
            #anchor="w",
            command = self.fNavigation_Receiver_button_event)
        self.fNavigation_Receiver_button.grid(row=3, column=0, sticky="ew")

        self.fNavigation_TxModuleInternal_button = ctk.CTkButton(self.fNavigation,
            text = "Tx Module (internal)",
            corner_radius=0, height=40, border_spacing=10,
            #image=self.add_user_image,
            #anchor="w",
            command = self.fNavigation_TxModuleInternal_button_event)
        self.fNavigation_TxModuleInternal_button.grid(row=4, column=0, sticky="ew")

        self.fNavigation_LuaScript_button = ctk.CTkButton(self.fNavigation,
            text = "Lua Script",
            corner_radius=0, height=40, border_spacing=10,
            #image=self.add_user_image,
            #anchor="w",
            command = self.fNavigation_LuaScript_button_event)
        self.fNavigation_LuaScript_button.grid(row=5, column=0, sticky="ew")

        # appearance options

        self.fNavigation_SetAppearanceMode_menu = ctk.CTkOptionMenu(self.fNavigation,
            values=["Light", "Dark", "System"],
            command=self.fNavigation_SetAppearanceMode_menu_event)
        self.fNavigation_SetAppearanceMode_menu.grid(row=6, column=0, padx=20, pady=20, sticky="s")

        #self.fNavigation_SetColorTheme_menu = ctk.CTkOptionMenu(self.fNavigation,
        #    values=["Blue", "Green", "Dark-Blue"],
        #    command=self.fNavigation_SetColorTheme_menu_event)
        #self.fNavigation_SetColorTheme_menu.grid(row=7, column=0, padx=20, pady=20, sticky="s")

    def fNavigation_select_frame_by_name(self, name):
        # show selected frame, and adjust color
        if name == "tx_module_ext":
            self.fNavigation_TxModuleExternal_button.configure(
                fg_color=self.fNavigation_selected_color,
                hover_color=self.fNavigation_selected_hover_color
                )
            self.fTxModuleExternal.grid(row=0, column=1, sticky="nsew")
        else:
            self.fNavigation_TxModuleExternal_button.configure(
                fg_color=self.fNavigation_fg_color,
                hover_color=self.fNavigation_hover_color)
            self.fTxModuleExternal.grid_forget()

        if name == "receiver":
            self.fNavigation_Receiver_button.configure(
                fg_color=self.fNavigation_selected_color,
                hover_color=self.fNavigation_selected_hover_color)
            self.fReceiver.grid(row=0, column=1, sticky="nsew")
        else:
            self.fNavigation_Receiver_button.configure(
                fg_color=self.fNavigation_fg_color,
                hover_color=self.fNavigation_hover_color)
            self.fReceiver.grid_forget()

        if name == "tx_module_int":
            self.fNavigation_TxModuleInternal_button.configure(
                fg_color=self.fNavigation_selected_color,
                hover_color=self.fNavigation_selected_hover_color)
            self.fTxModuleInternal.grid(row=0, column=1, sticky="nsew")
        else:
            self.fNavigation_TxModuleInternal_button.configure(
                fg_color=self.fNavigation_fg_color,
                hover_color=self.fNavigation_hover_color)
            self.fTxModuleInternal.grid_forget()

        if name == "lua_script":
            self.fNavigation_LuaScript_button.configure(
                fg_color=self.fNavigation_selected_color,
                hover_color=self.fNavigation_selected_hover_color)
            self.fLuaScript.grid(row=0, column=1, sticky="nsew")
        else:
            self.fNavigation_LuaScript_button.configure(
                fg_color=self.fNavigation_fg_color,
                hover_color=self.fNavigation_hover_color)
            self.fLuaScript.grid_forget()

    def fNavigation_TxModuleExternal_button_event(self):
        self.fNavigation_select_frame_by_name("tx_module_ext")

    def fNavigation_Receiver_button_event(self):
        self.fNavigation_select_frame_by_name("receiver")

    def fNavigation_TxModuleInternal_button_event(self):
        self.fNavigation_select_frame_by_name("tx_module_int")

    def fNavigation_LuaScript_button_event(self):
        self.fNavigation_select_frame_by_name("lua_script")

    def fNavigation_SetAppearanceMode_menu_event(self, opt):
        ctk.set_appearance_mode(opt)

    #def fNavigation_SetColorTheme_menu_event(self, opt):
    #    ctk.set_default_color_theme(opt.lower())


    #--------------------------------------------------
    #-- Tx Module (external) frame
    #--------------------------------------------------

    def initTxModuleExternalFrame(self):
        self.fTxModuleExternal = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fTxModuleExternal.grid_columnconfigure(0, weight=0)
        self.fTxModuleExternal.grid_columnconfigure(1, weight=1)
        self.fTxModuleExternal.grid_rowconfigure(5, weight=1)

        wrow = 0

        # Device Type
        self.fTxModuleExternal_DeviceType_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Device Type",
            )
        self.fTxModuleExternal_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_DeviceType_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=440, # this sets a min width, can grow larger
            #dynamic_resizing = False, # when false it prevents the box to grow with the entry
            command=self.fTxModuleExternal_DeviceType_menu_event)
        self.fTxModuleExternal_DeviceType_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fTxModuleExternal_FirmwareVersion_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Firmware Version",
            )
        self.fTxModuleExternal_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=440,
            command=self.fTxModuleExternal_FirmwareVersion_menu_event)
        self.fTxModuleExternal_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fTxModuleExternal_FirmwareFile_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Firmware File",
            )
        self.fTxModuleExternal_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_FirmwareFile_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=440,
            command=self.fTxModuleExternal_FirmwareFile_menu_event)
        self.fTxModuleExternal_FirmwareFile_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fTxModuleExternal_fFlash = ctk.CTkFrame(self.fTxModuleExternal, corner_radius=0, fg_color="transparent")
        self.fTxModuleExternal_fFlash.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        self.fTxModuleExternal_Flash_button = CTkFlashButton(self.fTxModuleExternal_fFlash,
            text = "Flash Tx Module",
            #fg_color="green", hover_color="#006400",
            command = self.fTxModuleExternal_Flash_button_event)
        self.fTxModuleExternal_Flash_button.grid(row=0, column=0)

        self.fTxModuleExternal_ComPort_menu = CTkCompPortOptionMenu(self.fTxModuleExternal_fFlash,
            porttype = 'esp,tx',
            values=['COM1'],
            width=10,
            )#command=self.fTxModuleExternal_ComPort_menu_event)
        self.fTxModuleExternal_ComPort_menu.grid(row=0, column=1, padx=20)
        self.fTxModuleExternal_ComPort_menu.grid_remove() # grid_remove() memorizes settings, grid_forget() looses them

        #-- Wireless Bridge --
        self.fTxModuleExternal_fWirelessBridge = ctk.CTkFrame(self.fTxModuleExternal, corner_radius=0, fg_color="transparent")
        self.fTxModuleExternal_fWirelessBridge.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="we")
        self.fTxModuleExternal_fWirelessBridge.grid_columnconfigure(0, weight=1)
        wrow += 1

        self.fTxModuleExternal_WirelessBridge_label = ctk.CTkLabel(self.fTxModuleExternal_fWirelessBridge,
            text="Wireless Bridge",
            font=ctk.CTkFont(weight="bold")
            )
        self.fTxModuleExternal_WirelessBridge_label.grid(row=0, column=0, sticky="w")

        self.fTxModuleExternal_WirelessBridgeFlash_button = CTkFlashButton(self.fTxModuleExternal_fWirelessBridge,
            text = "Flash Wireless Bridge",
            command = self.fTxModuleExternal_WirelessBridgeFlash_button_event)
        self.fTxModuleExternal_WirelessBridgeFlash_button.grid(row=1, column=0, pady=(20,0))

        #-- Description text box --
        self.fTxModuleExternal_Description_textbox = CTkInfoTextbox(self.fTxModuleExternal,
            #height=100,
            font=("Courier New",12),
            #activate_scrollbars=False,
            )
        self.fTxModuleExternal_Description_textbox.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        wrow += 1

        self.fTxModuleExternal_fWirelessBridge.grid_remove() # pack_forget() did not work!
        self.fTxModuleExternal_Description_textbox.setText("downloading metadata...\n")
        #self.fTxModuleExternal_Description_textbox.grid_remove()

    def fTxModuleExternal_ComPort_HandleIt(self):
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        chipset = self.txDeviceTypeDict[device_type]['chipset']
        if 'stm32' in chipset:
            self.fTxModuleExternal_ComPort_menu.grid_remove()
        elif 'esp32' in chipset:
            self.fTxModuleExternal_ComPort_menu.update()
            self.fTxModuleExternal_ComPort_menu.grid()

    def fTxModuleExternal_UpdateWidgets(self):
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleExternal_FirmwareFile_menu.get()
        _, _, description, wireless = self.get_metadata('tx', device_type, firmware_filename)
        if wireless != None:
            self.fTxModuleExternal_fWirelessBridge.grid()
        else:
            self.fTxModuleExternal_fWirelessBridge.grid_remove()
        text, tag = '', None
        if 'dev' in self.fTxModuleExternal_FirmwareVersion_menu.get():
            text, tag = warning_dev_version, warning_dev_version_tag
        if description != None:
            text += description
        if text != '':
            self.fTxModuleExternal_Description_textbox.grid()
            self.fTxModuleExternal_Description_textbox.setText(text, tag)
        else:
            self.fTxModuleExternal_Description_textbox.grid_remove()

    def fTxModuleExternal_Startup(self):
        res = self.updateTxModuleExternalFirmwareFiles()
        self.fTxModuleExternal_ComPort_HandleIt()
        self.fTxModuleExternal_UpdateWidgets()
        return res

    def fTxModuleExternal_DeviceType_menu_event(self, opt):
        self.updateTxModuleExternalFirmwareFiles()
        self.fTxModuleExternal_ComPort_HandleIt()
        self.fTxModuleExternal_UpdateWidgets()

    def fTxModuleExternal_FirmwareVersion_menu_event(self, opt):
        self.updateTxModuleExternalFirmwareFiles()
        self.fTxModuleExternal_UpdateWidgets()

    def fTxModuleExternal_FirmwareFile_menu_event(self, opt):
        self.fTxModuleExternal_UpdateWidgets()

    def fTxModuleExternal_Flash_button_event(self):
        self.flashTxModuleExternalFirmware()

    def fTxModuleExternal_WirelessBridgeFlash_button_event(self):
        self.flashTxModuleExternalWirelessBridgeFirmware()


    #--------------------------------------------------
    #-- Receiver frame
    #--------------------------------------------------

    def initReceiverFrame(self):
        self.fReceiver = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fReceiver.grid_columnconfigure(1, weight=1)
        self.fReceiver.grid_columnconfigure(2, weight=0)
        self.fReceiver.grid_rowconfigure(5, weight=1)

        wrow = 0

        # Device Type
        self.fReceiver_DeviceType_label = ctk.CTkLabel(self.fReceiver,
            text="Device Type")
        self.fReceiver_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_DeviceType_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=440,
            command=self.fReceiver_DeviceType_menu_event)
        self.fReceiver_DeviceType_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fReceiver_FirmwareVersion_label = ctk.CTkLabel(self.fReceiver,
            text="Firmware Version")
        self.fReceiver_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=440,
            command=self.fReceiver_FirmwareVersion_menu_event)
        self.fReceiver_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fReceiver_FirmwareFile_label = ctk.CTkLabel(self.fReceiver,
            text="Firmware File")
        self.fReceiver_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_FirmwareFile_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=440,
            command=self.fReceiver_FirmwareFile_menu_event)
        self.fReceiver_FirmwareFile_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fReceiver_Flash_button = CTkFlashButton(self.fReceiver,
            text = "Flash Receiver",
            command = self.fReceiver_Flash_button_event)
        self.fReceiver_Flash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        # Flash Method Frame
        self.fReceiver_Flashmethod_label = ctk.CTkLabel(self.fReceiver,
            text="Flash Method")
        self.fReceiver_Flashmethod_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_fFlashMethod = ctk.CTkFrame(self.fReceiver, corner_radius=0, fg_color="transparent")
        self.fReceiver_fFlashMethod.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        self.fReceiver_Flashmethod_menu = ctk.CTkOptionMenu(self.fReceiver_fFlashMethod,
            #values=["-"],
            width=140,
            command=self.fReceiver_Flashmethod_menu_event)
        self.fReceiver_Flashmethod_menu.grid(row=0, column=0, padx=0, sticky="w")

        self.fReceiver_ComPort_menu = CTkCompPortOptionMenu(self.fReceiver_fFlashMethod,
            porttype = 'esp,usbttl',
            values=['COM1'],
            width=10,
            )#command=self.fReceiver_ComPort_menu_event)
        self.fReceiver_ComPort_menu.grid(row=0, column=1, padx=20)

        self.fReceiver_Serialx_menu = ctk.CTkOptionMenu(self.fReceiver_fFlashMethod,
            values=['SERIAL1','SERIAL2','SERIAL3','SERIAL4','SERIAL5','SERIAL6','SERIAL7','SERIAL8'],
            width=120,
            )#command=self.fReceiver_Serialx_menu_event)
        self.fReceiver_Serialx_menu.grid(row=0, column=1, padx=20)

        #self.fReceiver_Flashmethod_label.grid_remove()
        #self.fReceiver_fFlashMethod.grid_remove()
        #self.fReceiver_Serialx_menu.grid_remove()

        #-- Description text box --
        self.fReceiver_Description_textbox = CTkInfoTextbox(self.fReceiver,
            #height=100,
            font=("Courier New",12),
            )
        self.fReceiver_Description_textbox.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        wrow += 1

        self.fReceiver_Description_textbox.setText("downloading metadata...\n")
        #self.fReceiver_Description_textbox.grid_remove()

    def fReceiver_UpdateWidgets(self):
        device_type = self.fReceiver_DeviceType_menu.get()
        firmware_filename = self.fReceiver_FirmwareFile_menu.get()
        _, flashmethod, description, wireless = self.get_metadata('rx', device_type, firmware_filename)
        text, tag = '', None
        if 'dev' in self.fReceiver_FirmwareVersion_menu.get():
            text, tag = warning_dev_version, warning_dev_version_tag
        if description != None:
            text += description
        if text != '':
            self.fReceiver_Description_textbox.grid()
            self.fReceiver_Description_textbox.setText(text, tag)
        else:
            self.fReceiver_Description_textbox.grid_remove()
        #flashmethod = 'esptool'
        #flashmethod = 'esptool,appassthru'
        #print(flashmethod)
        if flashmethod == None:
            self.fReceiver_Flashmethod_label.grid_remove()
            self.fReceiver_fFlashMethod.grid_remove()
        else:
            self.fReceiver_Flashmethod_label.grid()
            self.fReceiver_fFlashMethod.grid()
            menu_list = self.get_flashmethod_list_for_menu(flashmethod)
            self.fReceiver_Flashmethod_menu.configure(values=menu_list)
            self.fReceiver_Flashmethod_menu.set(menu_list[0])
            self.fReceiver_UpdateFlashMethodWidgets()

    def fReceiver_UpdateFlashMethodWidgets(self):
        sel = self.fReceiver_Flashmethod_menu.get()
        sel_flashmethod = self.get_flashmethod_from_menu_opt(sel)
        if sel_flashmethod == 'appassthru':
            self.fReceiver_ComPort_menu.grid_remove()
            self.fReceiver_Serialx_menu.grid()
        elif sel_flashmethod == 'esptool':
            self.fReceiver_ComPort_menu.grid()
            self.fReceiver_Serialx_menu.grid_remove()
        else:
            self.fReceiver_ComPort_menu.grid_remove()
            self.fReceiver_Serialx_menu.grid_remove()

    def fReceiver_ComPort_HandleIt(self):
        #device_type = self.fReceiver_DeviceType_menu.get()
        #firmware_filename = self.fReceiver_FirmwareFile_menu.get()
        #chipset, _, _, _ = self.get_metadata('rx', device_type, firmware_filename)
        self.fReceiver_ComPort_menu.update()

    def fReceiver_Startup(self):
        res = self.updateReceiverFirmwareFiles()
        self.fReceiver_ComPort_HandleIt()
        self.fReceiver_UpdateWidgets()
        return res

    def fReceiver_DeviceType_menu_event(self, opt):
        self.updateReceiverFirmwareFiles()
        self.fReceiver_ComPort_HandleIt()
        self.fReceiver_UpdateWidgets()

    def fReceiver_FirmwareVersion_menu_event(self, opt):
        self.updateReceiverFirmwareFiles()
        self.fReceiver_UpdateWidgets()

    def fReceiver_FirmwareFile_menu_event(self, opt):
        self.fReceiver_UpdateWidgets()

    def fReceiver_Flash_button_event(self):
        self.flashReceiverFirmware()

    def fReceiver_Flashmethod_menu_event(self, opt):
        self.fReceiver_UpdateFlashMethodWidgets()


    #--------------------------------------------------
    #-- Tx Module (internal) frame
    #--------------------------------------------------

    def initTxModuleInternalFrame(self):
        self.fTxModuleInternal = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fTxModuleInternal.grid_columnconfigure(1, weight=1)
        self.fTxModuleInternal.grid_rowconfigure(5, weight=1)

        wrow = 0

        # Device Type
        self.fTxModuleInternal_DeviceType_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Device Type",
            )
        self.fTxModuleInternal_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_DeviceType_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=440,
            command=self.fTxModuleInternal_DeviceType_menu_event)
        self.fTxModuleInternal_DeviceType_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fTxModuleInternal_FirmwareVersion_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Firmware Version",
            )
        self.fTxModuleInternal_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=440,
            command=self.fTxModuleInternal_FirmwareVersion_menu_event)
        self.fTxModuleInternal_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fTxModuleInternal_FirmwareFile_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Firmware File",
            )
        self.fTxModuleInternal_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_FirmwareFile_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=440,
            command=self.fTxModuleInternal_FirmwareFile_menu_event)
        self.fTxModuleInternal_FirmwareFile_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fTxModuleInternal_Flash_button = CTkFlashButton(self.fTxModuleInternal,
            text = "Flash Tx Module",
            command = self.fTxModuleInternal_Flash_button_event)
        self.fTxModuleInternal_Flash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        #-- Wireless Bridge --
        self.fTxModuleInternal_fWirelessBridge = ctk.CTkFrame(self.fTxModuleInternal, corner_radius=0, fg_color="transparent")
        self.fTxModuleInternal_fWirelessBridge.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="we")
        self.fTxModuleInternal_fWirelessBridge.grid_columnconfigure(0, weight=1)
        wrow += 1

        self.fTxModuleInternal_WirelessBridge_label = ctk.CTkLabel(self.fTxModuleInternal_fWirelessBridge,
            text="Wireless Bridge",
            font=ctk.CTkFont(weight="bold")
            )
        self.fTxModuleInternal_WirelessBridge_label.grid(row=0, column=0, sticky="w")

        self.fTxModuleInternal_WirelessBridgeFlash_button = CTkFlashButton(self.fTxModuleInternal_fWirelessBridge,
            text = "Flash Wireless Bridge",
            command = self.fTxModuleInternal_WirelessBridgeFlash_button_event)
        self.fTxModuleInternal_WirelessBridgeFlash_button.grid(row=1, column=0, pady=(20,0))

        #-- Description text box --
        self.fTxModuleInternal_Description_textbox = CTkInfoTextbox(self.fTxModuleInternal,
            font=("Courier New",12),
            )
        self.fTxModuleInternal_Description_textbox.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        wrow += 1

        self.fTxModuleInternal_fWirelessBridge.grid_remove() # pack_forget() did not work!
        self.fReceiver_Description_textbox.setText("downloading metadata...\n")
        #self.fTxModuleInternal_Description_textbox.grid_remove()

    def fTxModuleInternal_UpdateWidgets(self):
        device_type = self.fTxModuleInternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleInternal_FirmwareFile_menu.get()
        _, _, description, wireless = self.get_metadata('txint', device_type, firmware_filename)
        if wireless != None:
            self.fTxModuleInternal_fWirelessBridge.grid()
        else:
            self.fTxModuleInternal_fWirelessBridge.grid_remove()
        text, tag = '', None
        if 'dev' in self.fTxModuleInternal_FirmwareVersion_menu.get():
            text, tag = warning_dev_version, warning_dev_version_tag
        if description != None:
            text += description
        if text != '':
            self.fTxModuleInternal_Description_textbox.grid()
            self.fTxModuleInternal_Description_textbox.setText(text, tag)
        else:
            self.fTxModuleInternal_Description_textbox.grid_remove()

    def fTxModuleInternal_Startup(self):
        res = self.updateTxModuleInternalFirmwareFiles()
        self.fTxModuleInternal_UpdateWidgets()
        return res

    def fTxModuleInternal_DeviceType_menu_event(self, opt):
        self.updateTxModuleInternalFirmwareFiles()
        self.fTxModuleInternal_UpdateWidgets()

    def fTxModuleInternal_FirmwareVersion_menu_event(self, opt):
        self.updateTxModuleInternalFirmwareFiles()
        self.fTxModuleInternal_UpdateWidgets()

    def fTxModuleInternal_FirmwareFile_menu_event(self, opt):
        self.fTxModuleInternal_UpdateWidgets()

    def fTxModuleInternal_Flash_button_event(self):
        self.flashTxModuleInternalFirmware()

    def fTxModuleInternal_WirelessBridgeFlash_button_event(self):
        self.flashTxModuleInternalWirelessBridgeFirmware()


    #--------------------------------------------------
    #-- Lua Script frame
    #--------------------------------------------------

    def initLuaScriptFrame(self):
        self.fLuaScript = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fLuaScript.grid_columnconfigure(1, weight=1)

        wrow = 0

        # Firmware Version
        self.fLuaScript_FirmwareVersion_label = ctk.CTkLabel(self.fLuaScript,
            text="Firmware Version",
            )
        self.fLuaScript_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fLuaScript_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fLuaScript,
            values=["downloading..."],
            width=440,
            command=self.fLuaScript_FirmwareVersion_menu_event)
        self.fLuaScript_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Radio Screen
        self.fLuaScript_RadioScreen_label = ctk.CTkLabel(self.fLuaScript,
            text="Radio Screen Type",
            )
        self.fLuaScript_RadioScreen_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fLuaScript_RadioScreen_menu = ctk.CTkOptionMenu(self.fLuaScript,
            values=["downloading..."],
            width=440,
            )#command=self.fLuaScript_RadioScreen_menu_event)
        self.fLuaScript_RadioScreen_menu.grid(row=wrow, column=1, padx=(0,20), sticky="w")
        wrow += 1

        # Download Lua Script Button
        self.fLuaScript_Download_button = CTkFlashButton(self.fLuaScript,
            text = "Download Lua Script",
            command = self.fLuaScript_Download_button_event)
        self.fLuaScript_Download_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

    def fLuaScript_Startup(self):
        return self.updateLuaScriptFiles()

    def fLuaScript_FirmwareVersion_menu_event(self, opt):
        self.updateLuaScriptFiles()

    def fLuaScript_Download_button_event(self):
        initialfile = self.fLuaScript_RadioScreen_menu.get()
        if 'bw' in initialfile and 'compiled' in initialfile:
            initialfile = 'mLRS-bw-luac.lua'
        elif 'bw' in initialfile:
            initialfile = 'mLRS-bw.lua'
        else:
            initialfile = 'mLRS.lua'
        filename = filedialog.asksaveasfilename(
            initialfile = initialfile,
            filetypes = (('Lua files', '*.lua'),('All files', '*.*')),
            #defaultextension = '.lua',
            confirmoverwrite = True,
            )
        if not filename:
            return
        self.saveLuaScript(filename)


#--------------------------------------------------
#-- Main
#--------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.update()
    app.after(10,app.after_startup())
    app.mainloop()
    app.closed()

