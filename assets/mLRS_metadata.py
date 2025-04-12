#!/usr/bin/env python
#************************************************************
# Copyright (c) MLRS project
# GPL3
# https://www.gnu.org/licenses/gpl-3.0.de.html
# OlliW @ www.olliw.eu
#************************************************************
# mLRS Meta Data for mLRS Flasher Desktop App
# 6. Apr. 2025 002
#************************************************************


# this is easy enough to maintain by hand for the moment
#
# fname: holds a string which appears in the firmware file name and which allows to uniquely get the device type/brand
# chipset: we assume currently that a device type/brand does not use mixed chips

g_txModuleExternalDeviceTypeDict = {
    'MatekSys' :       { 'fname' : 'tx-matek',       'chipset' : 'stm32' },
    'FrSky R9' :       { 'fname' : 'tx-R9',          'chipset' : 'stm32' },
    'Wio E5' :         { 'fname' : 'tx-Wio-E5',      'chipset' : 'stm32' },
    'E77 MBL Kit' :    { 'fname' : 'tx-E77-MBLKit',  'chipset' : 'stm32' },
    'Easysolder' :     { 'fname' : 'tx-easysolder',  'chipset' : 'stm32' },
    'FlySky FRM 303' : { 'fname' : 'tx-FRM303',      'chipset' : 'stm32' },
    'RadioMaster' :    { 'fname' : 'tx-radiomaster', 'chipset' : 'esp32' },
    'BetaFPV' :        { 'fname' : 'tx-betafpv',     'chipset' : 'esp32' },
}

g_receiverDeviceTypeDict = {
    'MatekSys' :       { 'fname' : 'rx-matek',       'chipset' : 'stm32' },
    'FrSky R9' :       { 'fname' : 'rx-R9',          'chipset' : 'stm32' },
    'Wio E5' :         { 'fname' : 'rx-Wio-E5',      'chipset' : 'stm32' },
    'E77 MBL Kit' :    { 'fname' : 'rx-E77-MBLKit',  'chipset' : 'stm32' },
    'Easysolder' :     { 'fname' : 'rx-easysolder',  'chipset' : 'stm32' },
    'FlySky FRM 303' : { 'fname' : 'rx-FRM303',      'chipset' : 'stm32' },
    'RadioMaster' :    { 'fname' : 'rx-radiomaster', 'chipset' : 'espxx' }, #esp8285, esp32, esp32c3
    'BetaFPV' :        { 'fname' : 'rx-betafpv',     'chipset' : 'esp32' },
    'Bayck' :          { 'fname' : 'rx-bayck',       'chipset' : 'esp8285' },
    'SpeedyBee' :      { 'fname' : 'rx-speedybee',   'chipset' : 'esp8285' },
    'ELRS Generic' :   { 'fname' : 'rx-generic',     'chipset' : 'espxx' },
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

description_stm32_dfu_default = (
    "Flash method: DFU\n" +
    "  - connect to USB while pressing the button\n"
    )

description_stm32_stlink_default = (
    "Flash method: STLink\n" +
    "  - connect SWD pads to STLink\n"
    )

description_stm32_uart_default = (
    "Flash method: UART\n" +
    "  - connect Tx,Rx pads to USB-TTL adapter\n" +
    "  - select COM port\n" +
    "  - power up receiver while pressing the button\n"
    )

description_esp_esptool_uart_default = (
    "Flash method: esptool\n" +
    "  - connect Tx,Rx pads to USB-TTL adapter\n" +
    "  - select COM port\n" +
    "  - power up receiver while pressing the button\n"
    )

description_ap_passthru_default = (
    "In addition flashing via ArduPilot passthrough is supported.\n"
    )


g_targetDict = {
    #--------------------
    #-- Tx Modules
    #--------------------
    # stm32 defaults:
    # - 'flashmethod' : 'stlink'
    'tx-matek' : {
        'flashmethod' : 'dfu',
        'description' :
            description_stm32_dfu_default +
            "\nWireless bridge: HC04, cannot be flashed\n",
    },
    'tx-R9' : {
        'description' : description_stm32_stlink_default + "mLRS Flasher currently only supports STLink.\nPlease see docs for more details.\n",
    },
    'tx-E77-MBLKit' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'tx-Wio-E5' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'tx-easysolder' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'tx-FRM303' : {
        'description' : description_stm32_stlink_default + "mLRS Flasher currently only supports STLink.\nPlease see docs for more details.\n",
    },

    # esp32 tx module defaults
    # - 'flashmethod' : esptool with 'esp32'
    'tx-betafpv' : {
        'description' : "Not available (download failed)\n",
        'tx-betafpv-micro-1w-2400' : {
            'description' :
                "Flash method: connect to USB (select COM port)\n" +
                "\nWireless bridge: ESP8285\n" +
                "Dip switches need to be set as follow:\n" +
                "  1,2 on:    update firmware on main ESP32, USB connected to UARTO\n" +
                "  3,4 on:    normal operation mode, USB not used, UARTO connected to ESP8285\n" +
                "  5,6,7 on:  update firmware on ESP8285, USB connected to ESP8285 UART\n",
            'wireless' : {
                'chipset' : 'esp8266',
                'reset' : 'dtr',
                'baud' : 921600,
            },
        },
    },
    'tx-radiomaster' : {
        'description' : "Not available (download failed)\n",
        'tx-radiomaster-bandit' : {
            'description' :
                "Flash method: connect to USB (select COM port)\n" +
                "\nWireless bridge: ESP8285\n" +
                "For flashing the wireless bridge: \n" +
                "  - set 'Tx Ser Dest' to serial2\n" +
                "  - set 'Tx Ser Baudrate' to 115200\n" +
                "  - put Tx module into FLASH_ESP mode via OLED Actions page\n",
            'wireless' : {
                'chipset' : 'esp8266',
                'reset' : 'no dtr',
                'baud' : 115200,
            },
        },
        'tx-radiomaster-ranger' : {
            'description' :
                "Flash method: connect to USB (select COM port)\n" +
                "\nWireless bridge: ESP8285\n" +
                "For flashing the wireless bridge: \n" +
                "  - set 'Tx Ser Dest' to serial2\n" +
                "  - set 'Tx Ser Baudrate' to 115200\n" +
                "  - put Tx module into FLASH_ESP mode via OLED Actions page\n",
            'wireless' : {
                'chipset' : 'esp8266',
                'reset' : 'no dtr',
                'baud' : 115200,
            },
        },
        'tx-radiomaster-rp4td' : {
            'description' : "No description yet. Please see docs for details.\n",
        },
    },

    #--------------------
    #-- Internal Tx Modules
    #--------------------
    # esp32 internal tx module defaults
    # - 'flashmethod' : ...
    # - wireless-bridge: they all currently use a esp8285 backpack, and use the same wirelesss-bridge flash method
    'tx-jumper-internal' : {
        'description' :
            "Supported radios: T20 V2, T15, T14, T-Pro S\n" +
            "Flash method: radio passthrough\n" +
            "  - with radio powered up, connect to USB of your radio\n" + "  - select 'USB Serial (VCP)'\n" +
            "\nWireless bridge: ESP8285\n" +
            "For flashing the wireless bridge:\n" +
            "  - with radio powered up, connect to USB of your radio\n" + "  - select 'USB Serial (VCP)'\n",
        'wireless' : {
            'chipset' : 'esp8266',
            'baud' : 115200,
        },
    },
    'tx-radiomaster-internal' : {
        'description' :
            "Supported radios: TX16S, TX12, MT12, Zorro, Pocket, Boxer\n" +
            "Flash method: radio passthrough\n" +
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n" +
            "\nWireless bridge: ESP8285\n" +
            "For flashing the wireless bridge:\n" +
            "  - connect to USB of your radio and select 'USB Serial (VCP)'\n",
        'wireless' : {
            'chipset' : 'esp8266',
            'baud' : 115200,
        },
        'tx-radiomaster-internal-2400' : {
        },
        'tx-radiomaster-internal-boxer' : {
        },
    },

    #--------------------
    #-- Receivers
    #--------------------
    # stm32 defaults:
    # - 'flashmethod' : 'stlink'
    'rx-matek' : {
        'flashmethod' : 'dfu,appassthru',
        'description' : description_stm32_dfu_default + description_ap_passthru_default,
        'rx-matek-mr900-22' : {
            'flashmethod' : 'stlink,uart,appassthru',
            'description' : description_stm32_stlink_default + description_stm32_uart_default + description_ap_passthru_default,
        },
    },
    'rx-R9' : {
        'description' : description_stm32_stlink_default + "mLRS Flasher currently only supports STLink.\nPlease see docs for more details.\n",
        'rx-R9MX-l433cb': {
            'flashmethod' : 'stlink,appassthru',
            'description' : description_stm32_stlink_default + description_ap_passthru_default,
        }
    },
    'rx-E77-MBLKit' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'rx-Wio-E5' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'rx-easysolder' : {
        #'flashmethod' : 'stlink',
        'description' : description_stm32_stlink_default,
    },
    'rx-FRM303' : {
        'description' : description_stm32_stlink_default + "mLRS Flasher currently only supports STLink.\nPlease see docs for more details.\n",
    },

    # esp defaults:
    # - 'flashmethod' : 'esptool,appassthru'
    'rx-radiomaster' : {
        'flashmethod' : 'esptool,appassthru',
        'description' : description_esp_esptool_uart_default + description_ap_passthru_default,
        'rx-radiomaster-br3-900' : {
            'chipset' : 'esp8285',
        },
        'rx-radiomaster-rp4td-2400' : {
            'chipset' : 'esp32',
        },
        'rx-radiomaster-xr1-900' : {
            'chipset' : 'esp32c3',
        },
        'rx-radiomaster-xr4-900' : {
            'chipset' : 'esp32',
        },
    },
    'rx-betafpv' : {
        'chipset' : 'esp32',
        'flashmethod' : 'esptool,appassthru',
        'description' : description_esp_esptool_uart_default + description_ap_passthru_default,
    },
    'rx-bayck' : {
        'chipset' : 'esp8285',
        'flashmethod' : 'esptool,appassthru',
        'description' : description_esp_esptool_uart_default + description_ap_passthru_default,
    },
    'rx-speedybee' : {
        'chipset' : 'esp8285',
        'flashmethod' : 'esptool,appassthru',
        'description' : description_esp_esptool_uart_default + description_ap_passthru_default,
    },
    'rx-generic' : {
        'flashmethod' : 'esptool,appassthru',
        'description' : description_esp_esptool_uart_default + description_ap_passthru_default,
        'chipset' : 'esp8285',
        'rx-generic-2400-td-pa' : {
            'chipset' : 'esp32',
        },
        'rx-generic-900-td-pa' : {
            'chipset' : 'esp32',
        },
        'rx-generic-c3' : {
            'chipset' : 'esp32c3',
        },
        'rx-generic-lr1121-td' : {
            'chipset' : 'esp32',
        },
    },
}

