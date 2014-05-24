import crc16
import constants
import struct
import util


class BaseDatabaseRecord(object):
  FORMAT = None

  @classmethod
  def _CheckFormat(cls):
    if cls.FORMAT is None or not cls.FORMAT:
      raise NotImplementedError("Subclasses of %s need to define FORMAT"
                                % cls.__name__)

  @classmethod
  def _ClassFormat(cls):
    cls._CheckFormat()
    return struct.Struct(cls.FORMAT)

  @classmethod
  def _ClassSize(cls):
    return cls._ClassFormat().size

  @property
  def FMT(self):
    self._CheckFormat()
    return _ClassFormat()

  @property
  def SIZE(self):
    return self._ClassSize()

  @property
  def crc(self):
    return self.data[-1]

  def __init__(self, data, raw_data):
    self.raw_data = raw_data
    self.data = data
    self.check_crc()

  def check_crc(self):
    local_crc = self.calculate_crc()
    if local_crc != self.crc:
      raise constants.CrcError('Could not parse %s' % self.__class__.__name__)

  def dump(self):
    return ''.join('\\x%02x' % ord(c) for c in self.raw_data)

  def calculate_crc(self):
    return crc16.crc16(self.raw_data[:-2])

  @classmethod
  def Create(cls, data, record_counter):
    offset = record_counter * cls._ClassSize()
    raw_data = data[offset:offset + cls._ClassSize()]
    unpacked_data = cls._ClassFormat().unpack(raw_data)
    return cls(unpacked_data, raw_data)


class GenericTimestampedRecord(BaseDatabaseRecord):
  @property
  def system_time(self):
    return util.ReceiverTimeToTime(self.data[0])

  @property
  def display_time(self):
    return util.ReceiverTimeToTime(self.data[1])


class GenericXMLRecord(GenericTimestampedRecord):
  FORMAT = '<II490sH'

  @property
  def xmldata(self):
    data = self.data[2].replace("\x00", "")
    return data


class InsertionRecord(GenericTimestampedRecord):
  FORMAT = '<3IcH'

  @property
  def insertion_time(self):
    return util.ReceiverTimeToTime(self.data[2])

  @property
  def session_state(self):
    states = [None, 'REMOVED', 'EXPIRED', 'RESIDUAL_DEVIATION',
              'COUNTS_DEVIATION', 'SECOND_SESSION', 'OFF_TIME_LOSS',
              'STARTED', 'BAD_TRANSMITTER', 'MANUFACTURING_MODE']
    return states[ord(self.data[3])]

  def __repr__(self):
    return '%s:  state=%s' % (self.display_time, self.session_state)


class MeterRecord(GenericTimestampedRecord):
  FORMAT = '<2IHIH'

  @property
  def meter_glucose(self):
    return self.data[2]

  @property
  def meter_time(self):
    return util.ReceiverTimeToTime(self.data[3])

  def __repr__(self):
    return '%s: Meter BG:%s' % (self.display_time, self.meter_glucose)


class EventRecord(GenericTimestampedRecord):
  # sys_time,display_time,glucose,meter_time,crc
  FORMAT = '<2I2c2IH'

  @property
  def event_type(self):
    event_types = [None, 'CARBS', 'INSULIN', 'HEALTH', 'EXCERCISE',
                    'MAX_VALUE']
    return event_types[ord(self.data[2])]

  @property
  def event_sub_type(self):
    subtypes = {'HEALTH': [None, 'ILLNESS', 'STRESS', 'HIGH_SYMPTOMS',
                            'LOW_SYMTOMS', 'CYCLE', 'ALCOHOL'],
                'EXCERCISE': [None, 'LIGHT', 'MEDIUM', 'HEAVY',
                              'MAX_VALUE']}
    if self.event_type in subtypes:
      return subtypes[self.event_type][ord(self.data[3])]

  @property
  def display_time(self):
    return util.ReceiverTimeToTime(self.data[4])

  @property
  def event_value(self):
    value = self.data[5]
    if self.event_type == 'INSULIN':
      value = value / 100.0
    return value

  def __repr__(self):
    return '%s:  event_type=%s sub_type=%s value=%s' % (self.display_time, self.event_type,
                                    self.event_sub_type, self.event_value)


class EGVRecord(GenericTimestampedRecord):
  # uint, uint, ushort, byte, ushort
  # (system_seconds, display_seconds, glucose, trend_arrow, crc)
  FORMAT = '<2IHcH'

  @property
  def full_glucose(self):
    return self.data[2]

  @property
  def full_trend(self):
    return self.data[3]

  @property
  def display_only(self):
    return bool(self.full_glucose & constants.EGV_DISPLAY_ONLY_MASK)

  @property
  def glucose(self):
    return self.full_glucose & constants.EGV_VALUE_MASK

  @property
  def glucose_special_meaning(self):
    if self.glucose in constants.SPECIAL_GLUCOSE_VALUES:
      return constants.SPECIAL_GLUCOSE_VALUES[self.glucose]

  @property
  def is_special(self):
    return self.glucose_special_meaning is not None

  @property
  def trend_arrow(self):
    arrow_value = ord(self.full_trend) & constants.EGV_TREND_ARROW_MASK
    return constants.TREND_ARROW_VALUES[arrow_value]

  def __repr__(self):
    if self.is_special:
      return '%s: %s' % (self.display_time, self.glucose_special_meaning)
    else:
      return '%s: CGM BG:%s (%s) DO:%s' % (self.display_time, self.glucose,
                                           self.trend_arrow, self.display_only)
