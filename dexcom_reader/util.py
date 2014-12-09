import constants
import datetime
import os
import platform
import plistlib
import re
import subprocess


def ReceiverTimeToTime(rtime):
  return constants.BASE_TIME + datetime.timedelta(seconds=rtime)


def linux_find_usbserial(vendor, product):
  DEV_REGEX = re.compile('^tty(USB|ACM)[0-9]+$')
  for usb_dev_root in os.listdir('/sys/bus/usb/devices'):
    device_name = os.path.join('/sys/bus/usb/devices', usb_dev_root)
    if not os.path.exists(os.path.join(device_name, 'idVendor')):
      continue
    idv = open(os.path.join(device_name, 'idVendor')).read().strip()
    if idv != vendor:
      continue
    idp = open(os.path.join(device_name, 'idProduct')).read().strip()
    if idp != product:
      continue
    for root, dirs, files in os.walk(device_name):
      for option in dirs + files:
        if DEV_REGEX.match(option):
          return os.path.join('/dev', option)


def osx_find_usbserial(vendor, product):
  def recur(v):
    if hasattr(v, '__iter__') and 'idVendor' in v and 'idProduct' in v:
      if v['idVendor'] == vendor and v['idProduct'] == product:
        tmp = v
        while True:
          if 'IODialinDevice' not in tmp and 'IORegistryEntryChildren' in tmp:
            tmp = tmp['IORegistryEntryChildren']
          elif 'IODialinDevice' in tmp:
            return tmp['IODialinDevice']
          else:
            break

    if type(v) == list:
      for x in v:
        out = recur(x)
        if out is not None:
          return out
    elif type(v) == dict or issubclass(type(v), dict):
      for x in v.values():
        out = recur(x)
        if out is not None:
          return out

  sp = subprocess.Popen(['/usr/sbin/ioreg', '-k', 'IODialinDevice',
                         '-r', '-t', '-l', '-a', '-x'],
                        stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, _ = sp.communicate()
  plist = plistlib.readPlistFromString(stdout)
  return recur(plist)


def find_usbserial(vendor, product):
  """Find the tty device for a given usbserial devices identifiers.

  Args:
     vendor: (int) something like 0x0000
     product: (int) something like 0x0000

  Returns:
     String, like /dev/ttyACM0 or /dev/tty.usb...
  """
  if platform.system() == 'Linux':
    vendor, product = [('%04x' % (x)).strip() for x in (vendor, product)]
    return linux_find_usbserial(vendor, product)
  elif platform.system() == 'Darwin':
    return osx_find_usbserial(vendor, product)
  else:
    raise NotImplementedError('Cannot find serial ports on %s'
                              % platform.system())
