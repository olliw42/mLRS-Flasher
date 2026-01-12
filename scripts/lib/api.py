#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import requests
import copy
from .utils import json_log, json_error

g_jsonCacheDict = {}

# request json from url with caching
def request_json_dict(url, extension='', error_msg=''):
    if url in g_jsonCacheDict:
        return copy.deepcopy(g_jsonCacheDict[url])
    
    json_log(f'Fetching {url}...')
    res = None
    tries = 4
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
    
    g_jsonCacheDict[url] = copy.deepcopy(json_dict)
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
