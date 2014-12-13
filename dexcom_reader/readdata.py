import crc16
import constants
import database_records
import datetime
import serial
import sys
import time
import packetwriter
import struct
import re
import util
import xml.etree.ElementTree as ET
import numpy
import platform


class ReadPacket(object):
  def __init__(self, command, data):
    self._command = command
    self._data = data

  @property
  def command(self):
    return self._command

  @property
  def data(self):
    return self._data


class Dexcom(object):
  @staticmethod
  def FindDevice():
    return util.find_usbserial(constants.DEXCOM_G4_USB_VENDOR,
                               constants.DEXCOM_G4_USB_PRODUCT)

  @classmethod
  def LocateAndDownload(cls):
    device = cls.FindDevice()
    if not device:
      sys.stderr.write('Could not find Dexcom G4 Receiver!\n')
      sys.exit(1)
    else:
      dex = cls(device)
      print ('Found %s S/N: %s'
             % (dex.GetFirmwareHeader().get('ProductName'),
                dex.ReadManufacturingData().get('SerialNumber')))
      print 'Transmitter paired: %s' % dex.ReadTransmitterId()
      print 'Battery Status: %s (%d%%)' % (dex.ReadBatteryState(),
                                           dex.ReadBatteryLevel())
      print 'Record count:'
      print '- Meter records: %d' % (len(dex.ReadRecords('METER_DATA')))
      print '- CGM records: %d' % (len(dex.ReadRecords('EGV_DATA')))
      print ('- CGM commitable records: %d'
             % (len([not x.display_only for x in dex.ReadRecords('EGV_DATA')])))
      print '- Event records: %d' % (len(dex.ReadRecords('USER_EVENT_DATA')))
      print '- Insertion records: %d' % (len(dex.ReadRecords('INSERTION_TIME')))

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

  def write(self, *args, **kwargs):
    return self.port.write(*args, **kwargs)

  def read(self, *args, **kwargs):
    return self.port.read(*args, **kwargs)

  def readpacket(self, timeout=None):
    total_read = 4
    initial_read = self.read(total_read)
    all_data = initial_read
    if ord(initial_read[0]) == 1:
      command = initial_read[3]
      data_number = struct.unpack('<H', initial_read[1:3])[0]
      if data_number > 6:
        toread = abs(data_number-6)
        second_read = self.read(toread)
        all_data += second_read
        total_read += toread
        out = second_read
      else:
        out =  ''
      suffix = self.read(2)
      sent_crc = struct.unpack('<H', suffix)[0]
      local_crc = crc16.crc16(all_data, 0, total_read)
      if sent_crc != local_crc:
        raise constants.CrcError("readpacket Failed CRC check")
      num1 = total_read + 2
      return ReadPacket(command, out)
    else:
      raise constants.Error('Error reading packet header!')

  def Ping(self):
    self.WriteCommand(constants.PING)
    packet = self.readpacket()
    return ord(packet.command) == constants.ACK

  def WritePacket(self, packet):
    if not packet:
      raise constants.Error('Need a packet to send')
    packetlen = len(packet)
    if packetlen < 6 or packetlen > 1590:
      raise constants.Error('Invalid packet length')
    self.flush()
    self.write(packet)

  def WriteCommand(self, command_id, *args, **kwargs):
    p = packetwriter.PacketWriter()
    p.ComposePacket(command_id, *args, **kwargs)
    self.WritePacket(p.PacketString())

  def GenericReadCommand(self, command_id):
    self.WriteCommand(command_id)
    return self.readpacket()

  def ReadTransmitterId(self):
    return self.GenericReadCommand(constants.READ_TRANSMITTER_ID).data

  def ReadLanguage(self):
    lang = self.GenericReadCommand(constants.READ_LANGUAGE).data
    return constants.LANGUAGES[struct.unpack('H', lang)[0]]

  def ReadBatteryLevel(self):
    level = self.GenericReadCommand(constants.READ_BATTERY_LEVEL).data
    return struct.unpack('I', level)[0]

  def ReadBatteryState(self):
    state = self.GenericReadCommand(constants.READ_BATTERY_STATE).data
    return constants.BATTERY_STATES[ord(state)]

  def ReadRTC(self):
    rtc = self.GenericReadCommand(constants.READ_RTC).data
    return util.ReceiverTimeToTime(struct.unpack('I', rtc)[0])

  def ReadSystemTime(self):
    rtc = self.GenericReadCommand(constants.READ_SYSTEM_TIME).data
    return util.ReceiverTimeToTime(struct.unpack('I', rtc)[0])

  def ReadSystemTimeOffset(self):
    rtc = self.GenericReadCommand(constants.READ_SYSTEM_TIME_OFFSET).data
    return datetime.timedelta(seconds=struct.unpack('i', rtc)[0])

  def ReadDisplayTimeOffset(self):
    rtc = self.GenericReadCommand(constants.READ_DISPLAY_TIME_OFFSET).data
    return datetime.timedelta(seconds=struct.unpack('i', rtc)[0])

  def ReadDisplayTime(self):
    return self.ReadSystemTime() + self.ReadDisplayTimeOffset()

  def ReadGlucoseUnit(self):
    UNIT_TYPE = (None, 'mg/dL', 'mmol/L')
    gu = self.GenericReadCommand(constants.READ_GLUCOSE_UNIT).data
    return UNIT_TYPE[ord(gu[0])]

  def ReadClockMode(self):
    CLOCK_MODE = (24, 12)
    cm = self.GenericReadCommand(constants.READ_CLOCK_MODE).data
    return CLOCK_MODE[ord(cm[0])]

  def ReadDeviceMode(self):
    return self.GenericReadCommand(constants.READ_DEVICE_MODE).data

  def ReadManufacturingData(self):
    data = self.ReadRecords('MANUFACTURING_DATA')[0].xmldata
    return ET.fromstring(data)

  def flush(self):
    self.port.flush()

  def clear(self):
    self.port.flushInput()
    self.port.flushOutput()

  def GetFirmwareHeader(self):
    i = self.GenericReadCommand(constants.READ_FIRMWARE_HEADER)
    return ET.fromstring(i.data)

  def GetFirmwareSettings(self):
    i = self.GenericReadCommand(constants.READ_FIRMWARE_SETTINGS)
    return ET.fromstring(i.data)

  def DataPartitions(self):
    i = self.GenericReadCommand(constants.READ_DATABASE_PARTITION_INFO)
    return ET.fromstring(i.data)

  def ReadDatabasePageRange(self, record_type):
    record_type_index = constants.RECORD_TYPES.index(record_type)
    self.WriteCommand(constants.READ_DATABASE_PAGE_RANGE,
                      chr(record_type_index))
    packet = self.readpacket()
    return struct.unpack('II', packet.data)

  def ReadDatabasePage(self, record_type, page):
    record_type_index = constants.RECORD_TYPES.index(record_type)
    self.WriteCommand(constants.READ_DATABASE_PAGES,
                      (chr(record_type_index), struct.pack('I', page), chr(1)))
    packet = self.readpacket()
    assert ord(packet.command) == 1
    # first index (uint), numrec (uint), record_type (byte), revision (byte),
    # page# (uint), r1 (uint), r2 (uint), r3 (uint), ushort (Crc)
    header_format = '<2I2c4IH'
    header_data_len = struct.calcsize(header_format)
    header = struct.unpack_from(header_format, packet.data)
    header_crc = crc16.crc16(packet.data[:header_data_len-2])
    assert header_crc == header[-1]
    assert ord(header[2]) == record_type_index
    assert header[4] == page
    packet_data = packet.data[header_data_len:]

    return self.ParsePage(header, packet_data)

  def GenericRecordYielder(self, header, data, record_type):
    for x in range(header[1]):
      yield record_type.Create(data, x)

  def ParsePage(self, header, data):
    record_type = constants.RECORD_TYPES[ord(header[2])]
    generic_parser_map = {
      'USER_EVENT_DATA': database_records.EventRecord,
      'METER_DATA': database_records.MeterRecord,
      'INSERTION_TIME': database_records.InsertionRecord,
      'EGV_DATA': database_records.EGVRecord,
      'SENSOR_DATA': database_records.SensorRecord,
    }
    xml_parsed = ['PC_SOFTWARE_PARAMETER', 'MANUFACTURING_DATA']
    if record_type in generic_parser_map:
      return self.GenericRecordYielder(header, data,
                                       generic_parser_map[record_type])
    elif record_type in xml_parsed:
      return [database_records.GenericXMLRecord.Create(data, 0)]
    else:
      raise NotImplementedError('Parsing of %s has not yet been implemented'
                                % record_type)

  def ReadRecords(self, record_type):
    records = []
    assert record_type in constants.RECORD_TYPES
    start, end = self.ReadDatabasePageRange(record_type)
    if start != end or not end:
      end += 1
    for x in range(start, end):
      records.extend(self.ReadDatabasePage(record_type, x))
    return records


if __name__ == '__main__':
  Dexcom.LocateAndDownload()
