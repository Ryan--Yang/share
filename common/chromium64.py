#!/usr/bin/env python

import os
import commands
import argparse
import platform
import re
import sys

root_dir = ''
webview_dir = ''
args = ''
projects = []
android_target_arch = ''
chromium_target_arch = ''

patches = [
    # Patches borrowed from other groups
    #git fetch ssh://aia-review.intel.com/platform/system/core refs/changes/00/1700/2 && git cherry-pick FETCH_HEAD # atomic basic change
    #git fetch ssh://aia-review.intel.com/platform/system/core refs/changes/57/1957/1 && git cherry-pick FETCH_HEAD # atomic
    #git fetch ssh://aia-review.intel.com/platform/bionic refs/changes/43/1943/1 && git cherry-pick FETCH_HEAD # size_t
    #git fetch ssh://aia-review.intel.com/platform/frameworks/native refs/changes/50/1950/1 && git cherry-pick FETCH_HEAD # libbinder

    # Patches by our own
    'git fetch https://aia-review.intel.com/platform/external/chromium_org refs/changes/95/2395/2 && git checkout FETCH_HEAD',
]

def info(msg):
    print '[INFO] ' + msg + '.'

def warning(msg):
    print '[WARNING] ' + msg + '.'

def error(msg):
    print '[ERROR] ' + msg + '!'

def cmd(msg):
    print '[COMMAND] ' + msg

def execute(command, silent=False):
    if not silent:
        cmd(command)

    if os.system(command):
        error('Failed to execute')
        quit()

def bashify(command):
    return 'bash -c "' + command + '"'

def shell_source(shell_cmd):
    """Sometime you want to emulate the action of "source" in bash,
    settings some environment variables. Here is a way to do it."""
    import subprocess, os
    pipe = subprocess.Popen(". %s; env" % shell_cmd, stdout=subprocess.PIPE, shell=True)
    output = pipe.communicate()[0]
    for line in output.splitlines():
        (key, _, value) = line.partition("=")
        os.environ[key] = value

def get_script_dir():
    script_path = os.getcwd() + '/' + sys.argv[0]
    return os.path.split(script_path)[0]

def handle_option():
    global args
    parser = argparse.ArgumentParser(description = 'Script to sync, build Chromium x64',
                                     formatter_class = argparse.RawTextHelpFormatter,
                                     epilog = '''
examples:

  python %(prog)s

''')

    parser.add_argument('--patch', dest='patch', help='apply patch from Gerrit', action='store_true')
    parser.add_argument('--mk64', dest='mk64', help='generate mk for x86_64', action='store_true')
    parser.add_argument('-b', '--build', dest='build', help='build', action='store_true')
    parser.add_argument('-c', '--build-clean', dest='build_clean', help='clean build', action='store_true')
    parser.add_argument('--build-showcommands', dest='build_showcommands', help='build with detailed command', action='store_true')
    parser.add_argument('--build-onejob', dest='build_onejob', help='build with one job, and stop once failure happens', action='store_true')
    parser.add_argument('-d', '--root-dir', dest='root_dir', help='set root directory')
    args = parser.parse_args()

def setup():
    global root_dir, webview_dir, projects, android_target_arch, chromium_target_arch

    if not args.root_dir:
        root_dir = os.path.abspath(os.getcwd())
    else:
        root_dir = args.root_dir

    webview_dir = root_dir + '/external/chromium_org'
    os.chdir(webview_dir)

    r = os.popen('find -name ".git"')
    lines = r.read().split('\n')
    del lines[len(lines) - 1]
    for project in lines:
        project = project.replace('./', '')
        project = project.replace('.git', '')
        projects.append(project)

    android_target_arch = 'x86_64'
    chromium_target_arch = 'x64'

def patch():
    if not args.patch:
        return

    for patch in patches:
        pattern = re.compile('platform/(.*) (.*) &&')
        match = pattern.search(patch)
        project = match.group(1)
        change = match.group(2)
        command = 'git fetch ssh://aia-review.intel.com/platform/' + project + ' ' + change + ' && git cherry-pick FETCH_HEAD'
        os.chdir(root_dir + '/' + project)
        execute(command)

    os.chdir(webview_dir)

def mk64():
    if not args.mk64:
        return

    # Remove all the x64 mk files
    r = os.popen('find -name "*x86_64*.mk" -o -name "*x64*.mk"')
    files = r.read().split('\n')
    del files[len(files) - 1]
    for file in files:
        os.remove(file)

    # Generate raw .mk files
    command = bashify('export CHROME_ANDROID_BUILD_WEBVIEW=1 && . build/android/envsetup.sh --target-arch=' + chromium_target_arch + ' && android_gyp -Dwerror= ')
    execute(command)

    # Generate related x64 files according to raw .mk files
    file = open('GypAndroid.mk')
    lines = file.readlines()
    file.close()

    fw = open('GypAndroid.linux-' + android_target_arch + '.mk', 'w')

    # auto_x64 -> x64: target->target.linux-<android_target_arch>, host->host.linux-<android_target_arch>
    for line in lines:
        pattern = re.compile('\(LOCAL_PATH\)/(.*)')
        match = pattern.search(line)
        if match:
            auto_x64_file = match.group(1)
            x64_file = auto_x64_file.replace('target', 'target.linux-' + android_target_arch)
            x64_file = x64_file.replace('host', 'host.linux-' + android_target_arch)
            command = 'cp -f ' + auto_x64_file + ' ' + x64_file
            execute(command, True)

            line = line.replace('target', 'target.linux-' + android_target_arch)
            line = line.replace('host', 'host.linux-' + android_target_arch)
        fw.write(line)

    fw.close()

    # Check if x86 version has corresponding <target_arch> version
    # x86 -> x64: x86-><target_arch>, ia32-><target_arch>
    r = os.popen('find -name "*linux-x86.mk"')
    files = r.read().split('\n')
    del files[len(files) - 1]

    for x86_file in files:
        x64_file = x86_file.replace('x86', android_target_arch)
        x64_file = x64_file.replace('ia32', 'x64')
        if not os.path.exists(x64_file):
            print 'x64 version does not exist: ' + x86_file

    info('Number of x86 mk: ' + os.popen('find -name "*linux-x86.mk" |wc -l').read()[:-1])
    info('Number of x64 mk: ' + os.popen('find -name "*linux-' + android_target_arch + '.mk" |wc -l').read()[:-1])

def check_status():
    for project in projects:
        execute('git status ' + project)

def build():
    if not args.build:
        return

    command = '. ' + root_dir + '/build/envsetup.sh && lunch kvm_initrd_64bit-eng && '

    if args.build_clean:
        command += 'mma'
    else:
        command += 'mm'

    if args.build_showcommands:
        command += ' showcommands'

    if not args.build_onejob:
        command += ' -j16 -k'

    command = bashify(command)
    execute(command)

if __name__ == '__main__':
    handle_option()
    setup()
    patch()
    mk64()
    #check_status()
    build()
