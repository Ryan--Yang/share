#!/usr/bin/env python
#-*- coding: utf-8 -*-
#This script writed to auto build each revision chromium and save on the share folder

from util import *
import argparse
import commands
import os
import sys
import time

args = ''
work_dir = ''
src_dir = ''
dir_revert = '//ubuntu-ygu5-02.sh.intel.com/WebCatch/'
retry = 5
root_pwd = ''
blacklist = 'blacklist.log'

argparse.format_epilog = lambda self, formatter: self.epilog

def handle_option():
  global args
  parser = argparse.ArgumentParser(description = 'Script to update,\
                                   build and save content_shell_apk',
                                   formatter_class = \
                                   argparse.RawTextHelpFormatter,
                                   epilog = '''
examples:

  root:
  python %(prog)s --root password
  option:
  python %(prog)s -m revision
  

''')
  parser.add_argument('--root', dest='root_pwd', help='root password')                        
  parser.add_argument('-t', '--target', dest='target', help='target to build', choices=['chrome', 'webview', 'content_shell'], default='content_shell')
  parser.add_argument('-m', '--regress-revision', dest='revision',
                        help='build specific version')
  parser.add_argument('-high','--high-revision', dest='high', help='build high revision')
  parser.add_argument('-low','--low-revision', dest='low', help='build low revision', default='100000')
  parser.add_argument('--log',dest='log',help='set whether if log blacklist', choices=['true','false'], default='true')
  args = parser.parse_args()
  if len(sys.argv) <= 1:
    parser.print_help()
    
def setup_():
  global work_dir, src_dir
  src_dir = get_symbolic_link_dir()+'/'
  work_dir = '../project/chromium-android/'
  os.chdir(work_dir)
  work_dir= os.getcwd()+'/'
  
  #update src code to specific  revision
def reset_version(head):
  global args
  os.chdir(src_dir)
  if head:
    print 'head:'+head
    os.system('python chromium.py -u \'sync --revision src@'+head+'\''+' -d '+work_dir)
  else :
    return()

def update_package():
  import pexpect
  global args
  os.chdir(work_dir+'src/build/')
  update = pexpect.spawn('sudo /bin/sh install-build-deps-android.sh')
  try:
    i = update.expect(['[sudo] password','password'], timeout=5)
    print 'root password:'+args.root_pwd
    if i == 0 or i == 1:
      update.sendline(args.root_pwd)
      try:
        update.interact()
      except:
        warning('update error')
    else:
      quit(1)
  except pexpect.EOF:
    error('EOF')
    quit(1)
  except pexpect.TIMEOUT:
    error('TIMEOUT')
    quit(1)
    
def cache_apk(revision):
  import shutil
  apk_path = work_dir+'src/out/Release/apks/ContentShell.apk'
  if os.path.isfile(apk_path):
    dest_path = 'ContentShell@'+str(revision)+'.apk'
    try:
      execute('smbclient -c \'put '+apk_path+' out/content_shell_apk/'+dest_path+'\' '+dir_revert+' -N')
    except:
      time.sleep(2)
      execute('smbclient -c \'put '+apk_path+' out/content_shell_apk/'+dest_path+'\' '+dir_revert+' -N')
  else:
    error('can not find the file. please check whether if building is finished')
  
def build_content_shell():
  global args
  os.chdir(src_dir)
  try:
    execute('python chromium.py -b -c --target '+args.target+' -d '+work_dir)
  except:
    return(1)

def find_HEAD_by_revision(revision):
  os.chdir(work_dir+'src/')
  execute('git fetch origin')
  execute('git log origin/master > ../git.log')
  os.chdir(work_dir)
  commit_hash = ''
  vision = ''
  fileHandle = open('git.log','r')
  for line in fileHandle:
    lines = line.split()
    if not lines:
      continue
    if lines[0] == 'commit':
      commit_hash = lines[1]
    elif lines[0] == 'git-svn-id:':
      vision=(lines[1].split('@'))[1]
    else:
      continue
    if revision >= vision and vision != '':
      revision = vision
      fileHandle.close()
      os.remove('git.log')
      return commit_hash
  return 0
  
def find_empty_revision():
  global args
  high = '999999999'
  if args.high:
    high = args.high
  revision_list = {}
  os.chdir(work_dir+'src/')
  execute('git fetch origin')
  execute('git log origin/master > ../git.log')
  os.chdir(work_dir)
  commit_hash = ''
  vision = ''
  fileHandle = open('git.log','r')
  for line in fileHandle:
    lines = line.split()
    if not lines:
      continue
    if lines[0] == 'commit':
      commit_hash = lines[1]
    elif lines[0] == 'git-svn-id:':
      vision=(lines[1].split('@'))[1]
      if vision < high and vision > args.low:
        if not apk_is_exists(vision):
          if cache_build(commit_hash,vision):
	    log_blacklist(vision)
    else:
      continue

  info(' there are no specific revision not builded')
  return(0)

  #log apk which can't build
def log_blacklist(revision):
  os.chdir(src_dir)
  
  if not os.system('smbclient -c \'ls out/content_shell_apk/'+blacklist+'\' '+dir_revert+' -N'):
    execute('smbclient -c \'get  out/content_shell_apk/'+blacklist+' '+blacklist+'\' '+dir_revert+' -N')
  fileHandle = open(blacklist,'a')
  fileHandle.write('ContentShell '+'revision: '+revision+' status: CAN_NOT_BUILD \n')
  fileHandle.close  
  execute('smbclient -c \'put '+blacklist+' out/content_shell_apk/'+blacklist+'\' '+dir_revert+' -N')
  
  #check apk whether if  exists in the share folder
def apk_is_exists(vision):
  apk = 'ContentShell@'+vision+'.apk'
  return not os.system('smbclient -c \'ls out/content_shell_apk/'+apk+'\' '+dir_revert+' -N')
  
def cache_build(commit_hash,vision,log='true'):
  count = 0  
  while count < retry:
    print 'revision: '+vision
    reset_version(commit_hash)
    if build_content_shell():
      warning('Failed to execute build. retry again ... ('+str(count))
      if log == 'false':
	return(0)
      if count < 2:
        if args.root_pwd:
          update_package()
        else:
          os.chdir(work_dir+'src/build/')
          os.system('sudo /bin/sh install-build-deps-android.sh')
        count += 2
        continue
      elif count < 4 :
        os.chdir(work_dir+'src/out/Release/')
        execute('cp build.ninja ../')
        execute('rm * -f -r')
        execute('mv ../build.ninja build.ninja')
        count += 2
        continue
      else:
	return(1)
    cache_apk(vision)
    count = 7
  if count == 7:
    return(0)
  return(1)
 
def cache_specific_revision():
  global args
  if args.revision:
    commit_hash = find_HEAD_by_revision(args.revision)
    if cache_build(commit_hash,args.revision,args.log):
	  log_blacklist(args.revision)
    return(1)
  return(0)
 
if __name__ == '__main__':
  setup_()
  handle_option()
  cache_specific_revision()
  find_empty_revision()