#!/usr/bin/env python
#*******************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
# OlliW @ www.olliw.eu
#*******************************************************
# mLRS Flasher Desktop App
# 1. Feb. 2025 001
#********************************************************
app_version = '1.02.2025-001'

import os, sys, time
import subprocess
import re

from PIL import Image
import customtkinter as ctk
from customtkinter import ThemeManager, filedialog
import configparser

import requests
import json
import base64
import serial


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

'''
def os_system(arg):
    res = subprocess.call(arg)
    if res != 0:
        print('# ERROR (errno =',res,') DONE #')
        #print('Press Enter to continue')
        #input()
        #exit(1)
'''
def os_system(arg):
    res = os.system(arg)
    if res != 0:
        print('# ERROR (errno =',res,') DONE #')
        os.system("pause")
        exit(1)

python_cmd = '' # 'python' or 'python3' depending on installation

def _check_python_version(required_version):
    try:
        res = subprocess.check_output([required_version, "--version"], text=True)
        major_version = re.findall(r'\d', res)[0]
        return int(major_version)
    except:
        return 0

def check_python():
    # check if Python is installed and find which Python cmd to use
    global python_cmd
    if _check_python_version('python') == 3:
        python_cmd = 'python'
    elif _check_python_version('python3') == 3:
        python_cmd = 'python3'
    else:
        print("ERROR: Python 3 not found on your system. Please make sure Python 3 is available.")
        print('Press Enter to continue')
        input()
        exit(1)

check_python()


'''
--------------------------------------------------
STLink Flashing Tools
--------------------------------------------------
'''

def flashSTM32CubeProgrammer(programmer, firmware):
    if sys.platform.lower() == 'darwin':
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','mac','bin','STM32_Programmer_CLI')
    elif sys.platform.lower() == 'linux':
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','linux','bin','STM32_Programmer_CLI')
    else:
        ST_Programmer = os.path.join('thirdparty','STM32CubeProgrammer','win','bin','STM32_Programmer_CLI.exe')
    if 'dfu' in programmer:
        #os_system([ST_Programmer, '-c port=usb1', '-w "'+firmware+'"', '-v', '-g'])
        os_system(ST_Programmer + ' -c port=usb1 -w "'+firmware+'" -v -g')
        print('# DONE #')
    else:
        os_system(ST_Programmer + ' -c port=SWD freq=3900 -w "'+firmware+'" -v -g')
        print('# DONE #')


'''
--------------------------------------------------
Internal Tx Module Flashing Tools
--------------------------------------------------
'''

def find_radio_serial_ports():
    '''
    EdgeTx/OpenTx radio serial port is known to have vid == 0x0483, pid = 0x5740
    '''
    try:
        from serial.tools.list_ports import comports
        portList = list(comports())
    except:
        print('ERROR: find_radio_serial_port() [1]')
        return None
    radioportList = []
    for port in portList:
        if port.vid == 0x0483 and port.pid == 0x5740:
            if os.name == 'posix': # we do have more info on this os
                if port.manufacturer == 'OpenTX':
                    radioportList.append(port.device)
            else:
                radioportList.append(port.device)
    return radioportList


def do_msg(msg):
    print(msg)
    print('Press Enter to continue')
    input()


def do_error(msg):
    print(msg)
    print('Press Enter to continue')
    input()
    exit(1)


def execute_cli_command(ser, cmd, expected=None, timeout=1.0):
    ser.write(cmd+b'\n')
    res = b''
    tstart = time.perf_counter() #tstart = time.time()
    while True:
        tnow = time.perf_counter()
        if tnow - tstart > timeout:
            return None
        if ser.inWaiting() > 0:
            res += ser.read(1)
        if res[-4:] == b'\r\n> ': # we got it
            break
    #resList = res.split(b'\r\n')
    #print(resList)
    print(res)
    if expected and not expected in res:
        return None
    return res


def open_passthrough(baudrate = 115200, wirelessbridge = None):
    print()
    print('*** 1. Finding COM port of your radio ***')
    print()

    radioports_list = find_radio_serial_ports()
    if len(radioports_list) != 1:
        do_msg('Please power up your radio, connect the USB, and select "USB Serial (VCP)".')
        radioports_list = find_radio_serial_ports()
        if len(radioports_list) != 1:
            do_error('Sorry, something went wrong and we could not find the com port of your radio.')
    radioport = radioports_list[0]
    print('Your radio is on com port', radioport)

    try:
        s = serial.Serial(radioport)
        s.close()
    except:
        do_error('Sorry, something went wrong and we could not open the com port of your radio.')

    print()
    print('*** 2. Opening passthrough to the internal Tx Module ***')
    print()

    # This procedure seems to work independent on the selected Model
    # Seems to also work fine when the internal module is OFF

    ser = serial.Serial(radioport, timeout=0)
    ser.flush()

    res = execute_cli_command(ser, b'set pulses 0', expected = b'pulses stop')
    if not res:
        res = execute_cli_command(ser, b'set pulses 0', expected = b'pulses stop') # give it a 2nd try
        if not res:
            do_error('Sorry, something went wrong.')

    if not wirelessbridge:
        res = execute_cli_command(ser, b'set rfmod 0 bootpin 1', expected = b'bootpin set')
        if not res:
            do_error('Sorry, something went wrong.')
        time.sleep(.1)

    res = execute_cli_command(ser, b'set rfmod 0 power off')
    if not res:
        do_error('Sorry, something went wrong.')
    time.sleep(1)
    res = execute_cli_command(ser, b'set rfmod 0 power on')
    if not res:
        do_error('Sorry, something went wrong.')
    time.sleep(1)

    res = execute_cli_command(ser, b'set rfmod 0 bootpin 1', expected = b'bootpin set')
    if not res:
        do_error('Sorry, something went wrong.')
    time.sleep(1)
    res = execute_cli_command(ser, b'set rfmod 0 bootpin 0', expected = b'bootpin reset')
    if not res:
        do_error('Sorry, something went wrong.')

    cmd = b'serialpassthrough rfmod 0 ' + str(baudrate).encode('utf-8') + b'\n'
    ser.write(cmd)
    print(cmd)

    time.sleep(0.5)
    ser.close()

    return radioport


def flash_esp32(firmware, radioport, baudrate = 115200):
    print()
    print('*** 3. Flashing the internal Tx Module ***')
    print()
    print('The firmware to flash is:', firmware)

    assets_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets')
    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')

    args = (
        '--chip esp32' + ' ' +
        '--port "' + radioport + '" ' +
        '--baud ' + str(baudrate) + ' ' +
        '--before default_reset' + ' ' +
        '--after hard_reset write_flash' + ' ' +
        '-z' + ' ' +
        '--flash_mode dio' + ' ' +
        '--flash_freq 40m' + ' ' +
        '--flash_size 4MB 0x1000' + ' ' +
        '"' + os.path.join(assets_path,'esp32','bootloader.bin') + '" ' +
        '0x8000' + ' ' +
        '"' + os.path.join(assets_path,'esp32','partitions.bin') + '" ' +
        '0xe000' + ' ' +
        '"' + os.path.join(assets_path,'esp32','boot_app0.bin') + '" ' +
        '0x10000' + ' ' +
        '"' + os.path.join(temp_path, firmware) + '"'
        )
    print(args)
    #args = '--port "' + radioport + '" ' + '--baud ' + str(baudrate) + ' ' + 'flash_id'

    # TODO: can we catch if this was succesful?
    os_system(os.path.join('thirdparty','esptool','esptool.py') + ' ' + args)

    print()
    print('*** DONE ***')
    print()
    print('Please remove the USB cable.')
    print('Cheers, and have fun.')


def flash_esp8266_wirelessbridge(firmware, radioport, baudrate = 115200):
    print()
    print('*** 3. Flashing the internal Tx Module ***')
    print()
    print('The firmware to flash is:', firmware)

    assets_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets')
    temp_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'temp')

    args = (
        '--chip esp8266' + ' ' +
        '--port "' + radioport + '" ' +
        '--baud ' + str(baudrate) + ' ' +
        '--before no_reset' + ' ' +
        '--after soft_reset' + ' ' +
        'write_flash' + ' ' +
        '0x0' + ' ' +
        '"' + os.path.join(assets_path,'wirelessbridge-esp8266',firmware) + '"'
        )
    print(args)
    #args = '--port "' + radioport + '" ' + '--baud ' + str(baudrate) + ' ' + 'flash_id'

    os_system(os.path.join('thirdparty','esptool','esptool.py') + ' ' + args)

    print()
    print('*** DONE ***')
    print()
    print('Please remove the USB cable.')
    print('Cheers, and have fun.')


def flashInternalElrsTxModule(programmer, firmware):
    # firmware filename gives the complete path
    #print(filename)
    print(programmer)
    baudrate = 921600
    radioport = open_passthrough(baudrate)
    flash_esp32(firmware, radioport, baudrate)


def flashInternalElrsTxModuleWirelessBridge(programmer, firmware):
    #print(programmer)
    baudrate = 115200
    radioport = open_passthrough(baudrate, wirelessbridge = True)
    flash_esp8266_wirelessbridge(firmware, radioport, baudrate)



'''
--------------------------------------------------
API Helper
--------------------------------------------------
'''

g_TxModuleExternal_minimal_version = 'v1.3.00'
g_Receiver_minimal_version = 'v1.3.00'
g_TxModuleInternal_minimal_version = 'v1.3.05'
g_LuaScript_minimal_version = 'v1.3.00'


# this is easy enough to maintain by hand for the moment
g_deviceTypeDict = {
    'MatekSys' : 'matek',
    'FrSky R9' : 'R9',
    'FlySky FRM 303' : 'FRM303',
    'Wio E5' : 'Wio-E5',
    'E77 MBL Kit' : 'E77-MBLKit',
    'Easysolder' : 'easysolder'
}


g_txModuleInternalDeviceTypeDict = {
    'Jumper (T20, T20 V2, T15, T14, T-Pro S)' : 'jumper-internal',
    'RadioMaster (TX16S, TX12, MT12, Zorro, Pocket)' : 'radiomaster-internal',
}


def requestJsonDict(url, error_msg=''):
    try:
        res = requests.get(url, allow_redirects=True)
        if b'API rate limit exceeded' in res.content:
            print(res.content)
            print('DONWLOAD FAILED!')
            print(error_msg)
            return False
        jsonDict = res.json()
    except:
        print(res.content)
        print(error_msg)
        return None
    return jsonDict


def requestData(url, error_msg=''):
    jsonDict = None
    try:
        res = requests.get(url, allow_redirects=True)
        if b'API rate limit exceeded' in res.content:
            print(res.content)
            print('DONWLOAD FAILED!')
            print(error_msg)
            return False
        try:
            jsonDict = res.json()
        except:
            data = res.content
    except:
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
def getDevicesDict(txorrxortxint):
    if txorrxortxint == 'tx int':
        return g_txModuleInternalDeviceTypeDict
    else:
        return g_deviceTypeDict


# API for app
def getVersionsDict():
    # download mlrs_firmware_urls.json
    url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/tools/web/mlrs_firmware_urls.json'
    res = requestJsonDict(url, 'ERROR: getVersionsDict() [1]')
    if not res:
        return res
    resDict = res
    #print(resDict)

    # manipulate: add fields versionStr and gitUrl
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

        resDict[key]['gitUrl'] = 'https://api.github.com/repos/olliw42/mLRS/git/trees/' + resDict[key]['commit'] + '?recursive=true'

    # Figure out also the pre-release dev version. This needs work:
    # We need to read the main json, to get the current firmware folder url,
    # then read one file name in this folder, and extract the version part from the file name
    url_main = 'https://api.github.com/repos/olliw42/mLRS/git/trees/main'
    res = requestJsonDict(url_main, 'ERROR: getVersionsDict() [2]')
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

    url_main_firmware = key['url'] + '?recursive=true' # not so many, so we can afford getting them all
    res = requestJsonDict(url_main_firmware, 'ERROR: getVersionsDict() [2]')
    if not res:
        return res
    resMainFirmwareList = res['tree'] # it's a list of dictionaries
    #print(resMainFirmwareList)

    # firmware_filename looks like pre-release-stm32/rx-E77-MBLKit-wle5cc-400-tcxo-v1.3.01-@ae667b78.hex
    # find one file with a -@ in the name, and asumme it is representative for all dev versions
    # regex to get version and commit
    for key in resMainFirmwareList:
        if '-@' in key['path']: # this is one
            #print('we got one')
            #print(key)
            f = re.search(r'-(v\d\.\d+?\.\d+?-@[A-Za-z0-9]+?)\.', key['path'])
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
def getFilesListFromTree(txorrxortxintorlua, url, device=''):
    res = requestJsonDict(url, 'ERROR: getFilesListFromTree()')
    if not res:
        return res
    resList = res['tree'] # it's a list of dictionaries
    if txorrxortxintorlua == 'lua': # 'lua'
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            if 'lua/' not in key['path']:
                resList.remove(key)
            elif key['type'] != 'blob': # seems to not be needed, as all 'lua/' seem to be blob
                resList.remove(key)
            elif '.lua' not in key['path']: # only accept files with '.lua' extension
                resList.remove(key)
    elif txorrxortxintorlua == 'tx int': # 'tx int'
        #print(url, device)
        #print(resList)
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            if key['type'] != 'blob':
                resList.remove(key)
            elif '-stm32' in key['path']: # remove all files with '-stm32'
                resList.remove(key)
            elif '-esp' not in key['path']: # only accept files with '-esp', should be redundant
                resList.remove(key)
            elif 'tx-'+device not in key['path']: # only accept tx-device-internal
                resList.remove(key)
    else: # 'tx' or 'rx'
        for key in resList[:]: # creates a copy of the list, so we can easily remove
            if 'firmware/' not in key['path']:
                resList.remove(key)
            elif key['type'] != 'blob': # seems to not be needed, as all 'firmware/' seem to be blob
                resList.remove(key)
            elif '-esp' in key['path']: # remove all files with '-esp'
                resList.remove(key)
            elif '-stm32' not in key['path']: # only accept files with '-stm32', should be redundant
                resList.remove(key)
            elif txorrxortxintorlua+'-'+device not in key['path']: # only accept tx-device-xxx or rx-device-xxx
                resList.remove(key)

    #import pprint
    #F = open('filesfromtree-'+txorrxortxintorlua+'.txt', 'w')
    #F.write(url)
    #F.write('\n\r')
    #F.write( pprint.pformat(resList) )
    #F.close()

    return resList


def getFileAndWriteToDisk(url, filename):
    #url = 'https://api.github.com/repos/olliw42/mLRS/git/blobs/9cfb92d2de3f0582b6b33279abecd941885681d4'
    #filename = 'rx-matek-mr24-30-g431kb-can-v1.3.04.hex'
    data = requestData(url, 'ERROR: getFileAndWriteToDisk()')
    F = open(filename, 'wb')
    F.write(data)
    F.close()
    return True


# API for app
def flashDevice(programmer, device, url, filename):
    #print('flashDevice()')
    #print(device)
    #print(url)
    #print(filename)
    create_dir('temp')
    res = getFileAndWriteToDisk(url, os.path.join('temp',filename))
    if not res:
        print('ERROR: flashDevice()')
        return
    #print(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)),'temp',filename)
    #print(filepath)
    if 'wirelessbridge' in programmer:
        if 'internal' in programmer:
            if 'esp8285' in programmer:
                flashInternalElrsTxModuleWirelessBridge(programmer, filepath)
    elif 'stm32' in programmer:
        flashSTM32CubeProgrammer(programmer, filepath)
    elif 'esp32' in programmer:
        if 'internal' in programmer:
            flashInternalElrsTxModule(programmer, filepath)


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

class App(ctk.CTk):

    #--------------------------------------------------
    #-- Interface to low level handler
    #--------------------------------------------------

    # needs to be called only once at startup
    # calls getDevicesDict(), and updates the 'Device Type' widgets accordingly
    def updateDeviceTypes(self):
        self.txDeviceTypeDict = getDevicesDict('tx')
        keys = list(self.txDeviceTypeDict.keys())
        self.fTxModuleExternal_DeviceType_menu.configure(values=keys)
        self.fTxModuleExternal_DeviceType_menu.set(keys[0]) # this is needed to make the menu update itself

        self.rxDeviceTypeDict = getDevicesDict('rx')
        keys = list(self.rxDeviceTypeDict.keys())
        self.fReceiver_DeviceType_menu.configure(values=keys)
        self.fReceiver_DeviceType_menu.set(keys[0])

        self.txIntDeviceTypeDict = getDevicesDict('tx int')
        keys = list(self.txIntDeviceTypeDict.keys())
        self.fTxModuleInternal_DeviceType_menu.configure(values=keys)
        self.fTxModuleInternal_DeviceType_menu.set(keys[0])

    # needs to be called only once at startup
    # calls getVersionsDict(), and updates the Firmware Version' widgets accordingly
    def updateFirmwareVersions(self):
        self.firmwareVersionDict = getVersionsDict()
        if self.firmwareVersionDict:
            keys = []
            for key in list(self.firmwareVersionDict.keys()):
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

    # helper
    def _download_firmware_files(self, device_type, firmware_version, txorrxortxint):
        if txorrxortxint == 'tx':
            if self.txDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.txDeviceTypeDict[device_type] # that's the name of the device in the filename
        elif txorrxortxint == 'rx':
            if self.rxDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.rxDeviceTypeDict[device_type] # that's the name of the device in the filename
        elif txorrxortxint == 'tx int':
            if self.txIntDeviceTypeDict == None or self.firmwareVersionDict == None:
                return ['download failed...']
            device_type_f = self.txIntDeviceTypeDict[device_type] # that's the name of the device in the filename
        firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(device_type, device_type_f)
        #print(firmware_version, firmware_version_gitUrl)
        if txorrxortxint == 'tx':
            self.txFirmwareFilesList = getFilesListFromTree('tx', firmware_version_gitUrl, device_type_f) # must be self as list is needed later also
            firmwareFilesList = self.txFirmwareFilesList
        elif txorrxortxint == 'rx':
            self.rxFirmwareFilesList = getFilesListFromTree('rx', firmware_version_gitUrl, device_type_f) # must be self as list is needed later also
            firmwareFilesList = self.rxFirmwareFilesList
        elif txorrxortxint == 'tx int':
            self.txIntFirmwareFilesList = getFilesListFromTree('tx int', firmware_version_gitUrl, device_type_f) # must be self as list is needed later also
            firmwareFilesList = self.txIntFirmwareFilesList
        else:
            print('ERROR: _download_firmware_files() [1]')
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
        keys = self._download_firmware_files(device_type, firmware_version, 'tx')
        self.fTxModuleExternal_FirmwareFile_menu.configure(values=keys)
        self.fTxModuleExternal_FirmwareFile_menu.set(keys[0])

    # needs to be called whenever device type or firmware version changes
    # calls _download_firmware_files() to get the 'rx' file names in the tree, and updates Receiver 'Firmware Files' widget
    def updateReceiverFirmwareFiles(self):
        device_type = self.fReceiver_DeviceType_menu.get()
        firmware_version = self.fReceiver_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_firmware_files(device_type, firmware_version, 'rx')
        self.fReceiver_FirmwareFile_menu.configure(values=keys)
        self.fReceiver_FirmwareFile_menu.set(keys[0])

    # needs to be called whenever device type or firmware version changes
    # calls _download_firmware_files() to get the 'tx int' file names in the tree, and updates TxModuleInternal 'Firmware Files' widget
    def updateTxModuleInternalFirmwareFiles(self):
        device_type = self.fTxModuleInternal_DeviceType_menu.get()
        firmware_version = self.fTxModuleInternal_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_firmware_files(device_type, firmware_version, 'tx int')
        self.fTxModuleInternal_FirmwareFile_menu.configure(values=keys)
        self.fTxModuleInternal_FirmwareFile_menu.set(keys[0])

    # helper
    def _download_luascript_files(self, firmware_version):
        if self.firmwareVersionDict == None:
            return ['download failed...']
        firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(firmware_version, firmware_version_gitUrl)
        self.luaScriptFilesList = getFilesListFromTree('lua',firmware_version_gitUrl) # must be self as list is needed later also
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
    # calls _download_firmware_files() to get the '.lua' file names in the tree, and updates LuaScript 'Radio Screen Type' widget
    def updateLuaScriptFiles(self):
        firmware_version = self.fLuaScript_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        keys = self._download_luascript_files(firmware_version)
        self.fLuaScript_RadioScreen_menu.configure(values=keys)
        self.fLuaScript_RadioScreen_menu.set(keys[0])


    # calls flashDevice() for the selected device, firmware url, and filename, to initiate flashing
    def flashTxModuleExternalFirmware(self):
        #print('flashTxModuleExternalFirmware()')
        device_type = self.fTxModuleExternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleExternal_FirmwareFile_menu.get()
        if 'failed' in device_type or 'failed' in firmware_filename:
            print('ERROR: flashTxModuleExternalFirmware() [1]')
            return
        #print(firmware_filename)
        #print(self.txFirmwareFilesList)
        for key in self.txFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                if 'MatekSys' in device_type:
                    flashDevice('stm32 dfu', device_type, key['url'], firmware_filename)
                else:
                    flashDevice('stm32 stlink', device_type, key['url'], firmware_filename)
                return
        print('ERROR: flashTxModuleExternalFirmware() [2]')

    # calls flashDevice() for the selected device, firmware url, and filename, to initiate flashing
    def flashReceiverFirmware(self):
        device_type = self.fReceiver_DeviceType_menu.get()
        firmware_filename = self.fReceiver_FirmwareFile_menu.get()
        if 'failed' in device_type or 'failed' in firmware_filename:
            print('ERROR: flashReceiverFirmware() [1]')
            return
        #print(firmware_filename)
        #print(self.rxFirmwareFilesList)
        for key in self.rxFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                if 'MatekSys' in device_type: # TODO: this should be defined in a global structure !!
                    flashDevice('stm32 dfu', device_type, key['url'], firmware_filename)
                else:
                    flashDevice('stm32 stlink', device_type, key['url'], firmware_filename)
                return
        print('ERROR: flashReceiverFirmware() [2]')

    def flashTxModuleInternalFirmware(self):
        device_type = self.fTxModuleInternal_DeviceType_menu.get()
        firmware_filename = self.fTxModuleInternal_FirmwareFile_menu.get()
        if 'failed' in device_type or 'failed' in firmware_filename:
            print('ERROR: flashTxModuleInternalFirmware() [1]')
            return
        for key in self.txIntFirmwareFilesList:
            if firmware_filename in key['path']: # that's our firmware entry
                flashDevice('esp32 internal', device_type, key['url'], firmware_filename)
                return
        print('ERROR: flashTxModuleInternalFirmware() [2]')

    def flashTxModuleInternalWirelessBridgeFirmware(self):
        url = 'https://raw.githubusercontent.com/olliw42/mLRS/refs/heads/main/firmware/wirelessbridge-esp8266/mlrs-wireless-bridge-esp8266.ino.bin'
        firmware_filename = 'mlrs-wireless-bridge-esp8266.ino.bin'
        flashDevice('wirelessbridge internal esp8285', '', url, firmware_filename)


    # calls getFileAndWriteToDisk() for the selected filename, and saves it
    def saveLuaScript(self, filename):
        #print(filename)
        if self.firmwareVersionDict == None:
            return
        firmware_version = self.fLuaScript_FirmwareVersion_menu.get().split()[0] # remove the added ' (...)' from the version
        firmware_version_gitUrl = self.firmwareVersionDict[firmware_version]['gitUrl']
        #print(firmware_version, firmware_version_gitUrl)
        if self.luaScriptFilesList == None:
            print('ERROR: saveLuaScript() [1]')
            return
        #print(self.luaScriptFilesList)
        for key in self.luaScriptFilesList        :
            fpath, fname = os.path.split(key['path'])
            if fname.lower() in filename.lower():
                getFileAndWriteToDisk(key['url'], filename)
                return
        print('ERROR: saveLuaScript() [2]')


    #--------------------------------------------------
    #-- Init and Startup
    #--------------------------------------------------

    def __init__(self):
        super().__init__()

        self.title('mLRS Flasher Desktop App '+app_version)
        self.geometry('700x500')

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
        self.updateFirmwareVersions()

        self.updateTxModuleExternalFirmwareFiles()
        self.updateReceiverFirmwareFiles()
        self.updateTxModuleInternalFirmwareFiles()
        self.updateLuaScriptFiles()

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
        self.fTxModuleExternal.grid_columnconfigure(1, weight=1)

        wrow = 0

        # Device Type
        self.fTxModuleExternal_DeviceType_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Device Type",
            )
        self.fTxModuleExternal_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_DeviceType_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=300, # this sets a min width, can grow larger
            #dynamic_resizing = False, # when false it prevents the box to grow with the entry
            command=self.fTxModuleExternal_DeviceType_menu_event)
        self.fTxModuleExternal_DeviceType_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fTxModuleExternal_FirmwareVersion_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Firmware Version",
            )
        self.fTxModuleExternal_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=300,
            command=self.fTxModuleExternal_FirmwareVersion_menu_event)
        self.fTxModuleExternal_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fTxModuleExternal_FirmwareFile_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Firmware File",
            )
        self.fTxModuleExternal_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleExternal_FirmwareFile_menu = ctk.CTkOptionMenu(self.fTxModuleExternal,
            values=["downloading..."],
            width=300,
            command=self.fTxModuleExternal_FirmwareFile_menu_event)
        self.fTxModuleExternal_FirmwareFile_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fTxModuleExternal_Flash_button = ctk.CTkButton(self.fTxModuleExternal,
            text = "Flash Tx Module",
            command = self.fTxModuleExternal_Flash_button_event)
        self.fTxModuleExternal_Flash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        #-- Wireless Bridge --

        self.fTxModuleExternal_WirelessBridge_label = ctk.CTkLabel(self.fTxModuleExternal,
            text="Wireless Bridge",
            font=ctk.CTkFont(weight="bold")
            )
        self.fTxModuleExternal_WirelessBridge_label.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        wrow += 1

        # Wireless Bridge Flash Button
        self.fTxModuleExternal_WirelessBridgeFlash_button = ctk.CTkButton(self.fTxModuleExternal,
            text = "Flash Wireless Bridge",
            command = self.fTxModuleExternal_WirelessBridgeFlash_button_event)
        self.fTxModuleExternal_WirelessBridgeFlash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        self.fTxModuleExternal_WirelessBridge_label.grid_forget() # pack_forget() did not work!
        self.fTxModuleExternal_WirelessBridgeFlash_button.grid_forget()

    def fTxModuleExternal_DeviceType_menu_event(self, opt):
        self.updateTxModuleExternalFirmwareFiles()

    def fTxModuleExternal_FirmwareVersion_menu_event(self, opt):
        self.updateTxModuleExternalFirmwareFiles()

    def fTxModuleExternal_FirmwareFile_menu_event(self, opt):
        pass

    def fTxModuleExternal_Flash_button_event(self):
        self.flashTxModuleExternalFirmware()

    def fTxModuleExternal_WirelessBridgeFlash_button_event(self):
        pass


    #--------------------------------------------------
    #-- Receiver frame
    #--------------------------------------------------

    def initReceiverFrame(self):
        self.fReceiver = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fReceiver.grid_columnconfigure(1, weight=1)

        wrow = 0

        # Device Type
        self.fReceiver_DeviceType_label = ctk.CTkLabel(self.fReceiver,
            text="Device Type",
            )
        self.fReceiver_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_DeviceType_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=300,
            command=self.fReceiver_DeviceType_menu_event)
        self.fReceiver_DeviceType_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fReceiver_FirmwareVersion_label = ctk.CTkLabel(self.fReceiver,
            text="Firmware Version",
            )
        self.fReceiver_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=300,
            command=self.fReceiver_FirmwareVersion_menu_event)
        self.fReceiver_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fReceiver_FirmwareFile_label = ctk.CTkLabel(self.fReceiver,
            text="Firmware File",
            )
        self.fReceiver_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fReceiver_FirmwareFile_menu = ctk.CTkOptionMenu(self.fReceiver,
            values=["downloading..."],
            width=300,
            command=self.fReceiver_FirmwareFile_menu_event)
        self.fReceiver_FirmwareFile_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fReceiver_Flash_button = ctk.CTkButton(self.fReceiver,
            text = "Flash Receiver",
            command = self.fReceiver_Flash_button_event)
        self.fReceiver_Flash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)

    def fReceiver_DeviceType_menu_event(self, opt):
        self.updateReceiverFirmwareFiles()

    def fReceiver_FirmwareVersion_menu_event(self, opt):
        self.updateReceiverFirmwareFiles()

    def fReceiver_FirmwareFile_menu_event(self, opt):
        pass

    def fReceiver_Flash_button_event(self):
        self.flashReceiverFirmware()


    #--------------------------------------------------
    #-- Tx Module (internal) frame
    #--------------------------------------------------

    def initTxModuleInternalFrame(self):
        self.fTxModuleInternal = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.fTxModuleInternal.grid_columnconfigure(1, weight=1)

        wrow = 0

        # Device Type
        self.fTxModuleInternal_DeviceType_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Device Type",
            )
        self.fTxModuleInternal_DeviceType_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_DeviceType_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=300,
            command=self.fTxModuleInternal_DeviceType_menu_event)
        self.fTxModuleInternal_DeviceType_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware Version
        self.fTxModuleInternal_FirmwareVersion_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Firmware Version",
            )
        self.fTxModuleInternal_FirmwareVersion_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_FirmwareVersion_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=300,
            command=self.fTxModuleInternal_FirmwareVersion_menu_event)
        self.fTxModuleInternal_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Firmware File
        self.fTxModuleInternal_FirmwareFile_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Firmware File",
            )
        self.fTxModuleInternal_FirmwareFile_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fTxModuleInternal_FirmwareFile_menu = ctk.CTkOptionMenu(self.fTxModuleInternal,
            values=["downloading..."],
            width=300,
            command=self.fTxModuleInternal_FirmwareFile_menu_event)
        self.fTxModuleInternal_FirmwareFile_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Flash Button
        self.fTxModuleInternal_Flash_button = ctk.CTkButton(self.fTxModuleInternal,
            text = "Flash Tx Module",
            command = self.fTxModuleInternal_Flash_button_event)
        self.fTxModuleInternal_Flash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

        #-- Wireless Bridge --

        self.fTxModuleInternal_WirelessBridge_label = ctk.CTkLabel(self.fTxModuleInternal,
            text="Wireless Bridge",
            font=ctk.CTkFont(weight="bold")
            )
        self.fTxModuleInternal_WirelessBridge_label.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20, sticky="w")
        wrow += 1

        # Wireless Bridge Flash Button
        self.fTxModuleInternal_WirelessBridgeFlash_button = ctk.CTkButton(self.fTxModuleInternal,
            text = "Flash Wireless Bridge",
            command = self.fTxModuleInternal_WirelessBridgeFlash_button_event)
        self.fTxModuleInternal_WirelessBridgeFlash_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

    def fTxModuleInternal_DeviceType_menu_event(self, opt):
        self.updateTxModuleInternalFirmwareFiles()

    def fTxModuleInternal_FirmwareVersion_menu_event(self, opt):
        self.updateTxModuleInternalFirmwareFiles()

    def fTxModuleInternal_FirmwareFile_menu_event(self, opt):
        pass

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
            width=300,
            command=self.fLuaScript_FirmwareVersion_menu_event)
        self.fLuaScript_FirmwareVersion_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Radio Screen
        self.fLuaScript_RadioScreen_label = ctk.CTkLabel(self.fLuaScript,
            text="Radio Screen Type",
            )
        self.fLuaScript_RadioScreen_label.grid(row=wrow, column=0, padx=20, pady=20)
        self.fLuaScript_RadioScreen_menu = ctk.CTkOptionMenu(self.fLuaScript,
            values=["downloading..."],
            width=300,
            command=self.fLuaScript_RadioScreen_menu_event)
        self.fLuaScript_RadioScreen_menu.grid(row=wrow, column=1, padx=(1,20), sticky="w")
        wrow += 1

        # Download Color Script Button
        self.fLuaScript_Download_button = ctk.CTkButton(self.fLuaScript,
            text = "Download Lua Script",
            command = self.fLuaScript_Download_button_event)
        self.fLuaScript_Download_button.grid(row=wrow, column=0, columnspan=2, padx=20, pady=20)
        wrow += 1

    def fLuaScript_FirmwareVersion_menu_event(self, opt):
        self.updateLuaScriptFiles()

    def fLuaScript_RadioScreen_menu_event(self, opt):
        pass

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
    app.mainloop()
    app.closed()
