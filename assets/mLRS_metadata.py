#!/usr/bin/env python
#*******************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
# OlliW @ www.olliw.eu
#*******************************************************
# mLRS Meta Data for mLRS Flahser Desktop App
# 11. Feb. 2025 001
#********************************************************


# this is easy enough to maintain by hand for the moment
#
# fname: holds a string which appears in the firmware file name and which allows to uniquely get the device type/brand
# chipset: we assume currently that a device type/brand does not use mixed chips

g_txModuleExternalDeviceTypeDict = {
    'MatekSys' :       { 'fname' : 'tx-matek',       'chipset' : 'stm32' },
    'FrSky R9' :       { 'fname' : 'tx-R9',          'chipset' : 'stm32' },
    'FlySky FRM 303' : { 'fname' : 'tx-FRM303',      'chipset' : 'stm32' },
    'Wio E5' :         { 'fname' : 'tx-Wio-E5',      'chipset' : 'stm32' },
    'E77 MBL Kit' :    { 'fname' : 'tx-E77-MBLKit',  'chipset' : 'stm32' },
    'Easysolder' :     { 'fname' : 'tx-easysolder',  'chipset' : 'stm32' },
    'RadioMaster' :    { 'fname' : 'tx-radiomaster', 'chipset' : 'esp32' },
    'BetaFPV' :        { 'fname' : 'tx-betafpv',     'chipset' : 'esp32' },
}


g_receiverDeviceTypeDict = {
    'MatekSys' :       { 'fname' : 'rx-matek',       'chipset' : 'stm32' },
    'FrSky R9' :       { 'fname' : 'rx-R9',          'chipset' : 'stm32' },
    'FlySky FRM 303' : { 'fname' : 'rx-FRM303',      'chipset' : 'stm32' },
    'Wio E5' :         { 'fname' : 'rx-Wio-E5',      'chipset' : 'stm32' },
    'E77 MBL Kit' :    { 'fname' : 'rx-E77-MBLKit',  'chipset' : 'stm32' },
    'Easysolder' :     { 'fname' : 'rx-easysolder',  'chipset' : 'stm32' },
}


g_txModuleInternalDeviceTypeDict = {
    'Jumper Radio' :      { 'fname' : 'tx-jumper-internal',      'chipset' : 'esp32' },
    'RadioMaster Radio' : { 'fname' : 'tx-radiomaster-internal', 'chipset' : 'esp32' },
}


'''--------------------------------------------------
-- Target/firmware specific
--------------------------------------------------'''
# things which are target and/or firmware specific
# the upper level descriptor must be unique

g_targetDict = {
    #-- Tx Modules
    # stm32 defaults:
    # - 'flashmethod' : 'stlink'
    'tx-matek' : {
        'flashmethod' : 'dfu',
        'description' : 
            'Flash method: DFU, connect to USB\n\n' +
            'Wireless bridge: HC04, cannot be flashed\n',
    },
    'tx-E77-MBLKit' : {},
    'tx-easysolder' : {},
    'tx-FRM303' : {},
    'tx-R9' : {},
    'tx-Wio-E5' : {},

    # esp32 tx module defaults
    # - 'flashmethod' : esptool with 'esp32' 
    'tx-betafpv' : {
        'tx-betafpv-micro-1w-2400' : {
            'description' : 
                'Flash method: connect to USB (select COM port)\n\n' +
                'Wireless bridge: ESP8285\n' +
                'Dip switches need to be set as follow:\n' +
                '  1,2 on:    update firmware on main ESP32, USB connected to UARTO\n' +
                '  3,4 on:    normal operation mode, USB not used, UARTO connected to ESP8285\n' +
                '  5,6,7 on:  update firmware on ESP8285, USB connected to ESP8285 UART\n',
            'wireless' : {
                'chipset' : 'esp8266', 
                'reset' : 'dtr', 
                'baud' : 921600,
            },
        },
    },
    'tx-radiomaster' : {
        'tx-radiomaster-bandit' : {
            'description' : 
                'Flash method: connect to USB (select COM port)\n\n' +
                'Wireless bridge: ESP8285\n' +
                'For flashing the wireless bridge: \n' +
                '  - set Tx SerDest to serial2\n' +
                '  - set Tx SerBaudrate to 115200\n' +
                '  - put Tx module into FLASH_ESP mode via OLED Actions page\n',
            'wireless' : {
                'chipset' : 'esp8266',
                'reset' : 'no dtr', 
                'baud' : 115200,
            },
        },
        'tx-radiomaster-rp4td' : {},
    },

    # esp32 internal tx module defaults
    # - 'flashmethod' : ...
    # - wireless-bridge: they all currently use a esp8285 backpack, and use the same wirelesss-bridge flash method
    'tx-jumper-internal' : {
        'description' : 
            "Supported radios: T20 V2, T15, T14, T-Pro S\n" +
            "Flash method: radio passthrough\n" + 
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n\n" +
            "Wireless bridge: ESP8285\n" +
            "For flashing the wireless bridge:\n" +
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n",
    },
    'tx-radiomaster-internal' : {
        'description' : 
            "Supported radios: TX16S, TX12, MT12, Zorro, Pocket, Boxer\n" +
            "Flash method: radio passthrough\n" + 
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n\n" +
            "Wireless bridge: ESP8285\n" +
            "For flashing the wireless bridge:\n" +
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n",
        'tx-radiomaster-internal-2400' : {
        },
        'tx-radiomaster-internal-boxer' : {
        },
    },

    #-- Receivers
    # stm32 defaults:
    # - 'flashmethod' : 'stlink'
    'rx-matek' : {
        'flashmethod' : 'dfu',
        'rx-matek-mr900-22' : {
            'flashmethod' : 'stlink'
        },
    },
    'rx-E77-MBLKit' : {},
    'rx-easysolder' : {},
    'rx-FRM303' : {},
    'rx-R9' : {},
    'rx-Wio-E5' : {},
    
    # esp defaults:
    # - 'flashmethod' : ??
    'rx-bayck' : {},
    'rx-betafpv' : {},
    'rx-generic' : {},
    'rx-generic-c3-lr1121' : {},
    'rx-radiomaster' : {},
    'rx-speedybee' : {},
}

