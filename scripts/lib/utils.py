#!/usr/bin/env python
# ************************************************************
# Copyright (c) MLRS project
# GPL3
# 2026-01-11
# ************************************************************

import sys
import json
import re

# ensure stdout is unbuffered if possible
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

# ************************************************************
# JSON output helpers
# ************************************************************

# output a json object to stdout
def json_output(data):
    print(json.dumps(data), flush=True)


# output a log message in json format
def json_log(message, log_type='log'):
    json_output({'type': log_type, 'message': str(message)})


# output progress update
def json_progress(percent, message=''):
    json_output({'type': 'progress', 'percent': percent, 'message': message})


# output an error message
def json_error(message):
    json_log(message, 'error')


# output a success message
def json_success(message):
    json_log(message, 'success')


# ************************************************************
# output parsing helpers
# ************************************************************

# strip ANSI escape codes and partial fragments from CR-split lines
def strip_ansi(text):
    # full ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    text = ansi_escape.sub('', text)
    return text


# check if line is just ANSI escape code fragments (not meaningful output)
def is_ansi_garbage(text):
    stripped = text.strip()
    # match lines that are just partial ANSI codes like "[00;" or "32m" etc
    if re.match(r'^\[\d+;', stripped):  # [00; followed by anything
        return True
    if re.match(r'^\d+m\[', stripped):  # 32m[ - color code before progress bar
        return True
    if re.match(r'^\d+m$', stripped):   # just "32m" alone
        return True
    return False


# yield lines from stream, splitting on \n or \r
def read_lines_with_cr(stream):
    buf = bytearray()
    while True:
        # read one byte at a time for maximum responsiveness
        char = stream.read(1)
        if not char:
            if buf:
                yield buf.decode('utf-8', errors='ignore')
            break
        if char == b'\r' or char == b'\n':
            if buf:
                yield buf.decode('utf-8', errors='ignore')
                buf = bytearray()
        else:
            buf.extend(char)
            # safety: yield if buffer gets too long (e.g. no newlines)
            if len(buf) > 4096:
                yield buf.decode('utf-8', errors='ignore')
                buf = bytearray()
