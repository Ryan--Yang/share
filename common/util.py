#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import platform
import sys
import datetime
import commands
import argparse

host_os = platform.system()
args = ''
dir_stack = []

def get_datetime():
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d%H%M%S")

def info(msg):
    print "[INFO] " + msg + "."

def warning(msg):
    print '[WARNING] ' + msg + '.'

def error(msg):
    print "[ERROR] " + msg + "!"
    quit(1)

def execute(command, silent=False, catch=False):
    if not silent:
        _cmd(command)

    if catch:
        result = commands.getstatusoutput(command)
        if result[0] != 0:
            error('Failed to execute')
            quit(1)
        return result[1]
    else:
        if os.system(command):
            error('Failed to execute')
            quit(1)

def bashify(command):
    return 'bash -c "' + command + '"'

def is_system(name):
    if host_os == name:
        return True
    else:
        return False

def is_windows():
    if is_system('Windows'):
        return True
    else:
        return False

def is_linux():
    if is_system('Linux'):
        return True
    else:
        return False

def has_process(name):
    r = os.popen('ps auxf |grep -c ' + name)
    count = int(r.read())
    if count == 2:
        return False

    return True

def shell_source(shell_cmd, use_bash=False):
    import subprocess, os
    if use_bash:
        command = bashify('. ' + shell_cmd + '; env')
        pipe = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    else:
        pipe = subprocess.Popen('. %s; env' %shell_cmd, stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()[0]
    for line in output.splitlines():
        (key, _, value) = line.partition("=")
        os.environ[key] = value

def get_symbolic_link_dir():
    script_path = os.getcwd() + '/' + sys.argv[0]
    print script_path
    return os.path.split(script_path)[0]

def backup_dir(new_dir):
    global dir_stack
    dir_stack.append(os.getcwd())
    os.chdir(new_dir)

def restore_dir():
    global dir_stack
    os.chdir(dir_stack.pop())

################################################################################

def _cmd(msg):
    print '[COMMAND] ' + msg