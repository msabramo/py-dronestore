
import datetime
import nanotime

import merge
import model

class Attribute(object):
  '''Attributes define and compose a Model. A Model can be seen as a collection
  of attributes.

  An Attribute primarily defines a name, an associated data type, and a
  particular merge strategy.

  Attributes can have other options, including defining a default value, and
  validation for the data they hold.
  '''
  data_type = str
  default_strategy = merge.LatestObjectStrategy

  def __init__(self, name=None, default=None, required=False, strategy=None):

    if not strategy:
      strategy = self.default_strategy
    strategy = strategy(self)

    if not isinstance(strategy, merge.MergeStrategy):
      raise TypeError('mergeStrategy does not inherit from %s' % \
        merge.MergeStrategy)

    strategy.attribute = self

    self.name = name
    self.default = default
    self.required = required
    self.mergeStrategy = strategy


  def _attr_config(self, model_class, attr_name):
    '''Configure attribute for a given model.'''
    self.__model__ = model_class
    if self.name is None:
      self.name = attr_name

  def _attr_name(self):
    '''Returns the attribute name within the model instance.'''
    return '_' + self.name

  def rawData(self, instance):
    if instance is None:
      return None

    try:
      return getattr(instance, self._attr_name())
    except AttributeError:
      return None

  def setRawData(self, instance, rawData):
    setattr(instance, self._attr_name(), rawData)
    instance._isDirty = True

  def __get__(self, instance, model_class):
    '''Descriptor to aid model instantiation.'''
    if instance is None:
      return self

    try:
      return getattr(instance, self._attr_name())['value']
    except AttributeError:
      return self.default_value()

  def __set__(self, instance, value, default=False):
    '''Validate and Set the attribute on the model instance.'''
    value = self.validate(value)

    rawData = self.rawData(instance)
    if rawData is None:
      rawData = {}
      setattr(instance, self._attr_name(), rawData)

    # our attributes are idempotent, so if its the same, doesn't change state
    if 'value' in rawData and rawData['value'] == value:
      return

    rawData['value'] = value
    instance._isDirty = True
    self.mergeStrategy.setAttribute(instance, rawData, default=default)

  def default_value(self):
    '''The default value for a particular attribute.'''
    return self.default

  def validate(self, value):
    '''Assert that the provided value is compatible with this attribute.'''
    if self.empty(value):
      if self.required:
        raise ValueError('Attribute %s is required.' % self.name)

    if value is not None and not isinstance(value, self.data_type):
      try:
        value = self.data_type(value)
      except:
        errstr = 'value for attribute %s is not of type %s'
        raise TypeError(errstr % (self.name, self.data_type))

    return value

  def empty(self, value):
    '''Simple check to determine if value is empty.'''
    return not value





class StringAttribute(Attribute):
  '''Keep compatibility with App Engine by using basestrings as well'''
  data_type = basestring

  def __init__(self, multiline=False, **kwds):
    super(StringAttribute, self).__init__(**kwds)
    self.multiline = multiline

  def validate(self, value):
    if value is not None and not isinstance(value, self.data_type):
      value = str(value)

    value = super(StringAttribute, self).validate(value)

    if not self.multiline and value and '\n' in value:
      raise ValueError('Attribute %s is not multi-line' % self.name)

    return value


class KeyAttribute(StringAttribute):
  '''Attribute to store Keys.'''
  data_type = model.Key

  def __init__(self, **kwds):
    super(KeyAttribute, self).__init__(multiline=False, **kwds)


class IntegerAttribute(Attribute):
  '''Integer Attribute'''
  data_type = int

  def validate(self, value):
    value = super(IntegerAttribute, self).validate(value)
    if value is None:
      return value

    if not isinstance(value, (int, long)) or isinstance(value, bool):
      raise ValueError('Attribute %s must be an int or long, not a %s'
                          % (self.name, type(value).__name__))

    if value < -0x8000000000000000 or value > 0x7fffffffffffffff:
      raise ValueError('Property %s must fit in 64 bits' % self.name)

    return value

  def empty(self, value):
    '''0 is not empty.'''
    return value is None



class FloatAttribute(Attribute):
  '''Floating point Attribute'''
  data_type = float

  def empty(self, value):
    '''0 is not empty.'''
    return value is None


class BooleanAttribute(Attribute):
  '''Boolean Attribute'''
  data_type = bool

  def empty(self, value):
    '''False is not empty.'''
    return value is None



class TimeAttribute(Attribute):
  '''Attribute to store nanosecond times.'''
  data_type = nanotime.nanotime





class DateTimeAttribute(TimeAttribute):
  '''Attribute to store nanosecond times and return datetime objects.'''

  def __get__(self, instance, model_class):
    '''Descriptor to aid model instantiation.'''
    if instance is None:
      return self

    value = super(DateTimeAttribute, self).__get__(instance, model_class)
    return value.datetime()

  def __set__(self, instance, value, default=False):
    '''Set the attribute on the model instance.'''
    if not isinstance(value, datetime.datetime):
      raise TypeError('Incorrect type supplied. Expecting datetime.')

    value = nanotime.datetime(value)
    super(DateTimeAttribute, self).__set__(instance, value, default=default)





class ListAttribute(Attribute):
  '''Attribute to store lists.'''
  data_type = list
  data_value_type = str

  def __init__(self, value_type=None, **kwds):
    super(ListAttribute, self).__init__(**kwds)
    if value_type:
      self.data_value_type = value_type

  def validate(self, value):
    value = super(ListAttribute, self).validate(value)
    if value is None:
      return value

    for i in xrange(0, len(value)):
      val = value[i]
      if not isinstance(val, self.data_value_type):
        try:
          value[i] = self.data_value_type(val)
        except:
          errstr = 'internal value for attribute %s is not of type %s'
          raise TypeError(errstr % (self.name, self.data_value_type))

    return value

  def empty(self, value):
    '''[] is not empty.'''
    return value is None





class DictAttribute(ListAttribute):
  '''Attribute to store lists.'''
  data_type = dict
  data_value_type = str

  def validate(self, value):
    value = super(ListAttribute, self).validate(value)
    if value is None:
      return value

    for key, val in value.items():

      # Make sure all keys are strings
      if not isinstance(key, basestring):
        try:
          value[str(key)] = value[key]
          del value[key]
          key = str(key)
        except:
          errstr = 'internal key for attribute %s must be a string'
          raise TypeError(errstr % self.name)

      # Make sure all values are of type `data_value_type`
      if not isinstance(val, self.data_value_type):
        try:
          value[key] = self.data_value_type(val)
        except:
          errstr = 'internal value for attribute %s must be of type %s'
          raise TypeError(errstr % (self.name, self.data_value_type))

    return value

  def empty(self, value):
    '''{} is not empty.'''
    return value is None


