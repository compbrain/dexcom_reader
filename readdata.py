"""Dexcom G4 Platinum data reader.

Copyright 2013

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from curses import ascii as asciicc
import re
import serial
import sys
import time
import xml.etree.ElementTree as ET


class Dexcom(object):
  BASE_PREFIX = "\x01\x06\x00"

  def __init__(self, port):
    self._port_name = port
    self._port = None

  def Connect(self):
    if self._port is None:
      self._port = serial.Serial(port=self._port_name, baudrate=115200)

  def Disconnect(self):
    if self._port is not None:
      self._port.close()

  @property
  def port(self):
    if self._port is None:
      self.Connect()
    return self._port

  def Waiting(self, timeout=None):
    start_time = time.time()
    while True:
      if (timeout is not None) and (time.time() - start_time) > timeout:
        return 0
      n = self.port.inWaiting()
      if n:
        return n
      time.sleep(0.1)

  def write(self, *args, **kwargs):
    return self.port.write(*args, **kwargs)

  def read(self, *args, **kwargs):
    return self.port.read(*args, **kwargs)

  def readwaiting(self):
    waiting = self.Waiting()
    return self.read(waiting)

  def Handshake(self):
    self.write("%s\x0a\x5e\x65" % self.BASE_PREFIX)
    if self.readwaiting() == "%s\x01\x35\xd4" % self.BASE_PREFIX:
      return True

  def IdentifyDevice(self):
    iprefix = "\x01\x03\x01\x01"
    self.write("%s\x0b\x7f\x75" % self.BASE_PREFIX)
    i = self.readwaiting()
    # Strip prefix
    i = i[len(iprefix):]
    # Strip tail
    ta = i[-2:]
    assert ta == "\xd8\xd4"
    i = i[:-2]
    e = ET.fromstring(i)
    print 'Found %s' % e.get('ProductName')
    return e

  def flush(self):
    self.port.flush()

  def clear(self):
    self.port.flushInput()
    self.port.flushOutput()

  def CleanData(self, i):
    i = ''.join(c for c in i if ord(c) >= 32)
    return i

  def GetManufacturingParameters(self):
    #self.port.write("\x01\x07\x00\x10\x00\x0f\xf8")
    #self.readwaiting()
    #self.clear()
    self.write("\x01\x0c\x00\x11\x00\x00\x00\x00\x00\x01\x6e\x45")

    i = self.CleanData(self.readwaiting())
    i = i[8:-4]
    e = ET.fromstring(i)
    print 'Found %s (S/N: %s)' % (e.get('HardwarePartNumber'),
                                  e.get('SerialNumber'))
    return e

  def GetFirmwareHeader(self):
    self.write("\x01\x06\x00\x0b\x7f\x75")
    i = self.CleanData(self.readwaiting())[:-2]
    e = ET.fromstring(i)
    return e

  def Ping(self):
    self.write("\x01\x07\x00\x10\x02\x4d\xd8")
    self.readwaiting()
    self.write("\x01\x07\x00\x10\x02\x4d\xd8")
    self.readwaiting()
    self.flush()
    self.clear()

  def GetPcParams(self):
    self.write("\x01\x0c\x00\x11\x02\x00\x00\x00\x00\x01\x2e\xce")
    i =self.CleanData(self.readwaiting())[8:-3]
    e = ET.fromstring(i)
    return e

  def DataPartitions(self):
    self.write("\x01\x06\x00\x36\x81\x92")
    print self.readwaiting()
    self.write("\x01\x06\x00\x0f\xfb\x35")
    print self.readwaiting()
    print self.readwaiting()

d = Dexcom(sys.argv[1])

if d.Handshake():
  print "Connected successfully!"

print d.IdentifyDevice()
print d.GetManufacturingParameters()
print d.GetFirmwareHeader()
print d.GetPcParams()
