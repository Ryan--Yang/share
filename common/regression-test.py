#!/usr/bin/env python
#-*- coding: utf-8 -*-


from util import *
from selenium import webdriver
import argparse
import commands
import os
import sys
import time
import subprocess

args = ''
driver = webdriver
driver_pipe = subprocess.Popen
dir_revert = '//ubuntu-ygu5-02.sh.intel.com/WebCatch/'
log_file = ''
apk_list = {}

argparse.format_epilog = lambda self, formatter: self.epilog

def handle_option():
  global args
  parser = argparse.ArgumentParser(description = 'Script to run\
                                   benchmark on chrome for android',
                                   formatter_class = \
                                   argparse.RawTextHelpFormatter,
                                   epilog = '''
examples:

  python %(prog)s -g 218527 -b 226662 -t 'http://browsermark.rightware.com/tests' --average 3800

''')
  parser.add_argument('--driver-url', dest='ip', help='set driver ip', default='http://127.0.0.1')
  parser.add_argument('--port', dest='port', help='set driver port. default is 9515', default='9515')
  parser.add_argument('--package', dest='package_name', help='set android package name', default='org.chromium.content_shell_apk')
  parser.add_argument('-g', '--good-revision', dest='good_revision', type=int, help='high revision',required=True)
  parser.add_argument('-b', '--bad-revision', dest='bad_revision', type=int, help='low revision',required=True)
  parser.add_argument('-t', '--test-url', dest='test_url', help='run test by url', required=True)
  parser.add_argument('--average', dest='average', help='regression average score', required=True)
  parser.add_argument('--chromedriver', dest='driver', help='chromedriver path', default='chromedriver');
  args = parser.parse_args()
  if len(sys.argv) <= 1:
    parser.print_help()
    
def start_chromedriver():
  global driver_pipe,args
  command = args.driver+' --port='+args.port
  driver_pipe = subprocess.Popen(command, shell=True)
  time.sleep(2)

def stop_chromedriver():
  global driver_pipe
  execute('killall chromedriver')
  
def start_content_shell(ip, port, package_name):
  global driver
  capabilities = {
    'chromeOptions': {
      'androidPackage': package_name
    }
  }
  print 'start'
  driver = webdriver.Remote(ip+':'+port,capabilities)
  print 'driver start'
  time.sleep(1)
  
def run_test(url):
  global driver
  print 'run test'
  driver.get(url)
  flag = True
  info('Waiting the score...')
  while flag:
    time.sleep(1)
    status = driver.find_element_by_id("status")
    if status.text.find('Score') >= 0:
      print status.text.find('Score')
      flag = False
  score = status.text
  print score
  driver.quit()
  return score

def install_apk(apk_path):
    import shutil
    shutil.move(apk_path,'ContentShell.apk')
    execute('adb install -r ContentShell.apk')
    shutil.move('ContentShell.apk',apk_path)
  
def get_apk(vision):
  apk = 'ContentShell@'+str(vision)+'.apk'
  try :
    execute('smbclient -c \'get  out\content_shell_apk\\'+apk+' '+apk+'  \' '+dir_revert+' -N')
  except:
    quit(0)
  return apk

  
def log(revision,result,status):
  global log_file
  filehandle = open(log_file,'a')
  print revision
  text = 'ContentShell '+'revision: '+str(revision)+' score: '+result+' status: '+status+'\n'
  filehandle.write(text)
  filehandle.close
  
def test(revision):
  global args
  apk_path = get_apk(revision)
  install_apk(apk_path)
  start_content_shell(args.ip,args.port,args.package_name)
  result = run_test(args.test_url)
  return (result.split(': '))[1]
   
  #use dichotomy method to find regression revision
def dichotomy_match(low,high):
  global args,apk_list

  if low >= high:
    info('can\' t find the regression apk')
    return(1)
  mid = (low+high)/2
  flag = test(apk_list[mid]) 
  if  flag > args.average:
    log((apk_list[mid]),flag,'NORMAL')
    if (mid+1) < len(apk_list):
      result = test(apk_list[mid+1])
      if result <= args.average:
        log(apk_list[mid+1],result,'REGRESSION')
        return(0)
    dichotomy_match(mid,high)
  elif flag <= args.average:
    log((apk_list[mid]),flag,'NORMAL')
    if (mid-1) >= 0:
      result = test(apk_list[mid-1])
      if result > args.average:
        log((apk_list[mid-1]),result,'REGRESSION')
        return(0)
    dichotomy_match(low,mid)
  else:
    return(1)
  
def _setup():
  global log_file,args
  log_file = '../log/benchmark'+get_datetime()+'.log'
  execute('adb start-server')
  start_chromedriver()
  cache_exist_apks()
  
  filehandle = open(log_file,'a')
  filehandle.write('good_revision: '+str(args.good_revision)+' bad_revision: '+str(args.bad_revision)+' average:'+str(args.average)+'\n')
  filehandle.close
  
def cache_exist_apks():
  global args,apk_list
  i = 0
  flag = args.good_revision
  while flag <= args.bad_revision:
    apk = 'ContentShell@'+str(flag)+'.apk'
    if not os.system('smbclient -c \'ls out/content_shell_apk/'+apk+'\' '+dir_revert+' -N'):
      apk_list[i] = flag
      i += 1
    flag += 1
    
def cleanup():
  stop_chromedriver()
  execute('rm *.apk')
  #execute('smbclient -c \'put '+log_file+' log/'+log_file+'\' '+dir_revert+' -N')
  

if __name__ == '__main__':
  handle_option()
  _setup()
  dichotomy_match(0,len(apk_list))
  cleanup()
