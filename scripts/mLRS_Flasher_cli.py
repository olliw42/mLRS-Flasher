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

import sys
import os
import argparse

# resolve paths relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# add thirdparty to path for pymavlink
sys.path.insert(0, os.path.join(ROOT_DIR, 'thirdparty', 'mavlink'))

# add assets to path for metadata
sys.path.insert(0, os.path.join(ROOT_DIR, 'assets'))

# the lib package is in the same directory as this script.
# we need to make sure we can import it.
from lib import commands

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
        commands.cmd_list_versions(args)
    elif args.command == 'list-devices':
        commands.cmd_list_devices(args)
    elif args.command == 'list-firmware':
        commands.cmd_list_firmware(args)
    elif args.command == 'list-ports':
        commands.cmd_list_ports(args)
    elif args.command == 'get-metadata':
        commands.cmd_get_metadata(args)
    elif args.command == 'flash':
        commands.cmd_flash(args)
    elif args.command == 'download-lua':
        commands.cmd_download_lua(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
