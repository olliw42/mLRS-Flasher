#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import os
import sys
from .constants import ASSETS_PATH

# ensure we can find mLRS_metadata
if ASSETS_PATH not in sys.path:
    sys.path.insert(0, ASSETS_PATH)
import mLRS_metadata as mlrs_md


# resolve chipset from device and target metadata
def resolve_chipset(device_dict, target_dict, filename):
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


# lookup device dictionaries from metadata
def get_device_info(device_name, device_type=None):
    device_dict = {}
    target_dict = {}
    
    # if type is provided, search specifically
    dicts_to_search = []
    if device_type == 'tx':
        dicts_to_search = [mlrs_md.g_txModuleExternalDeviceTypeDict]
    elif device_type == 'rx':
        dicts_to_search = [mlrs_md.g_receiverDeviceTypeDict]
    elif device_type == 'txint':
        dicts_to_search = [mlrs_md.g_txModuleInternalDeviceTypeDict]
    else:
        # search all
        dicts_to_search = [
            mlrs_md.g_txModuleExternalDeviceTypeDict, 
            mlrs_md.g_receiverDeviceTypeDict, 
            mlrs_md.g_txModuleInternalDeviceTypeDict
        ]

    for d in dicts_to_search:
        if device_name in d:
            device_dict = d.get(device_name, {})
            fname = device_dict.get('fname', '')
            target_dict = mlrs_md.g_targetDict.get(fname, {})
            break
            
    return device_dict, target_dict
