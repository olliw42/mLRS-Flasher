#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import requests
import copy
import os
import json
import time
import tempfile
from .utils import json_log, json_error

# cache configuration
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'mLRS-Flasher')
CACHE_FILE = os.path.join(CACHE_DIR, 'api_cache.json')

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        try:
            os.makedirs(CACHE_DIR)
        except Exception:
            pass

def load_persistent_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_persistent_cache(data):
    ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


# request json from url with caching
def request_json_dict(url, extension='', error_msg=''):
    # check persistent cache first
    cached_data = load_persistent_cache()
    current_time = time.time()
    
    # generate a cache key (simple url based)
    cache_key = url + extension
    
    if cache_key in cached_data:
        entry = cached_data[cache_key]
        # check if cache is effective (valid for 10 minutes)
        if current_time - entry.get('timestamp', 0) < 600:
            return entry.get('data')
    
    json_log(f'Fetching {url}...')
    res = None
    tries = 4
    json_dict = None
    
    while tries > 0:
        try:
            res = requests.get(url + extension, allow_redirects=True, timeout=(3.05, 15))
            if res.status_code == 200:
                if b'API rate limit exceeded' in res.content:
                    json_error('GitHub API rate limit exceeded')
                    return None
                json_dict = res.json()
                break
            else:
                tries -= 1
        except Exception:
            tries -= 1
            if tries <= 0:
                json_error(f'Failed to fetch {url}')
                return None
    
    if json_dict is not None:
        # update cache
        cached_data[cache_key] = {
            'timestamp': current_time,
            'data': json_dict
        }
        save_persistent_cache(cached_data)
        
    return json_dict


# request binary/text data from url
def request_data(url, error_msg=''):
    json_log(f'Downloading {url}...')
    tries = 4
    while tries > 0:
        try:
            res = requests.get(url, allow_redirects=True, timeout=(3.05, 15))
            if res.status_code == 200:
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
            else:
                tries -= 1
        except Exception as e:
            tries -= 1
            if tries <= 0:
                json_error(f'Failed to download: {e}')
                return None
    return None
