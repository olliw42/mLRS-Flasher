#!/usr/bin/env python
#************************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
#************************************************************
# Open passthrough to internal Tx module of EdgeTx/OpenTx radios
# 15. Feb. 2025
#************************************************************

import os, sys, time
import serial, argparse


#--------------------------------------------------
#-- Internal Tx Module Flashing Tools
#--------------------------------------------------

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
                if port.manufacturer == 'OpenTX' or port.manufacturer == 'EdgeTX':
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
    sys.exit(1)


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


def find_radioport():
    radioports_list = find_radio_serial_ports()
    if len(radioports_list) != 1:
        do_msg("Please power up your radio, connect the USB, and select 'USB Serial (VCP)'.")
        radioports_list = find_radio_serial_ports()
        if len(radioports_list) != 1:
            do_error('Sorry, something went wrong and we could not find the com port of your radio.')
    radioport = radioports_list[0]
    print('Your radio is on com port', radioport)
    return radioport


def open_passthrough(comport = None, baudrate = 115200, wirelessbridge = None):
    print()
    print('*** 1. Finding COM port of your radio ***')
    print()

    if comport:
        radioport = comport
        print('Your radio is on com port', radioport)
    else:    
        radioport = find_radioport()

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

    print()
    if wirelessbridge:
        print('You are ready to flash the wireless bridge on your internal Tx module now!')
    else:
        print('You are ready to flash the internal Tx module now!')

    return radioport


#--------------------------------------------------
#-- Main
#--------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = 'Initialize EdgeTX/OpenTx passthrough to internal Tx module'
        )
    parser.add_argument("-c", "--com", help="Com port for passthrough communication. Examples: com5, /dev/ttyACM0")
    parser.add_argument("-b", "--baud", type=int, default=115200, help = 'Baudrate for passthrough communication')
    parser.add_argument("-w", "--wirelessbridge", action='store_true', help = 'Wirelessbridge passthrough')
    parser.add_argument("-findport", action='store_true', help = 'Find port')
    args = parser.parse_args()

    if args.findport:
        radioport = mlrs_find_apport()
        sys.exit(-int(radioport[3:])) # report back com port, for use in batch file

    radioport = open_passthrough(comport = args.com, baudrate = args.baud, wirelessbridge = args.wirelessbridge)
    
    sys.exit(-int(radioport[3:]))



'''
example usage in batch file

@edgetxInitPassthru.py passthru_args
@if %ERRORLEVEL% GEQ 1 EXIT /B 1
@if %ERRORLEVEL% LEQ 0 set /a RADIOPORT=-%ERRORLEVEL%
@ECHO.
@ECHO *** 3. Flashing the internal Tx Module ***
@ECHO.
@ECHO The firmware to flash is: firmware
@thirdparty/esptool/esptool.py esptool_args
@ECHO.
@ECHO *** DONE ***
@ECHO.
@ECHO Please remove the USB cable.
@ECHO Cheers, and have fun.
###    F.write('@pause'+'\n')
   if os_system_is_frozen_app(): F.write('@pause'+'\n')

'''
