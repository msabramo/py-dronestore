import unittest
import hashlib
import nanotime

from dronestore.util import serial
from dronestore.model import *

from .util import RandomGen


class Person(Model):
  first = StringAttribute(default="Firstname")
  last = StringAttribute(default="Lastname")
  phone = StringAttribute(default="N/A")
  age = IntegerAttribute(default=0)
  gender = StringAttribute()




class KeyTests(unittest.TestCase):

  def __subtest_basic(self, string):
    fixedString = Key.removeDuplicateSlashes(string)
    self.assertEqual(Key(string)._str, fixedString)
    self.assertEqual(Key(string), Key(string))
    self.assertEqual(str(Key(string)), fixedString)
    self.assertEqual(repr(Key(string)), fixedString)
    self.assertEqual(Key(string).name(), fixedString.rsplit('/')[-1])

    self.assertRaises(TypeError, cmp, Key(string), string)

    split = fixedString.split('/')
    if len(split) > 1:
      self.assertEqual(Key('/'.join(split[:-1])), Key(string).parent())
    else:
      self.assertRaises(ValueError, Key.parent, Key(string))

    if len(split) > 2:
      self.assertEqual(split[-2], Key(string).type())
    else:
      self.assertRaises(ValueError, Key.type, Key(string))

  def test_basic(self):
    self.__subtest_basic('')
    self.__subtest_basic('abcde')
    self.__subtest_basic('disahfidsalfhduisaufidsail')
    self.__subtest_basic('/fdisahfodisa/fdsa/fdsafdsafdsafdsa/fdsafdsa/')
    self.__subtest_basic(u'4215432143214321432143214321')
    self.__subtest_basic('/fdisaha////fdsa////fdsafdsafdsafdsa/fdsafdsa/')


  def test_ancestry(self):
    k1 = Key('/A/B/C')
    k2 = Key('/A/B/C/D')

    self.assertEqual(k1._str, '/A/B/C')
    self.assertEqual(k2._str, '/A/B/C/D')
    self.assertTrue(k1.isAncestorOf(k2))
    self.assertEqual(k1.child('D'), k2)
    self.assertEqual(k1, k2.parent())

    self.assertRaises(TypeError, k1.isAncestorOf, str(k2))
    self.assertEqual(k1.type(), 'B')
    self.assertEqual(k2.type(), 'C')
    self.assertEqual(k2.type(), k1.name())

  def test_hashing(self):

    def randomKey():
      return Key('/herp/' + RandomGen.randomString() + '/derp')

    keys = {}

    for i in range(0, 200):
      key = randomKey()
      while key in keys.values():
        key = randomKey()

      hstr = str(hash(key))
      self.assertFalse(hstr in keys)
      keys[hstr] = key

    for key in keys.values():
      hstr = str(hash(key))
      self.assertTrue(hstr in keys)
      self.assertEqual(key, keys[hstr])

  def test_random(self):
    keys = set()
    for i in range(0, 1000):
      random = Key.randomKey()
      self.assertFalse(random in keys)
      keys.add(random)
    self.assertEqual(len(keys), 1000)





class VersionTests(unittest.TestCase):

  def test_blank(self):
    blank = Version(Key('/BLANK'))
    self.assertEqual(blank.hash(), Version.BLANK_HASH)
    self.assertEqual(blank.type(), '')
    self.assertEqual(blank.shortHash(5), Version.BLANK_HASH[0:5])
    self.assertEqual(blank.committed(), nanotime.nanotime(0))
    self.assertEqual(blank.created(), nanotime.nanotime(0))
    self.assertEqual(blank.parent(), Version.BLANK_HASH)

    self.assertEqual(blank, Version(Key('/BLANK')))
    self.assertTrue(blank.isBlank())


  def test_creation(self):

    h1 = hashlib.sha1('derp').hexdigest()
    h2 = hashlib.sha1('herp').hexdigest()
    now = nanotime.now()

    sr = serial.SerialRepresentation()
    sr['key'] = '/A'
    sr['hash'] = h1
    sr['parent'] = h2
    sr['created'] = now.nanoseconds()
    sr['committed'] = now.nanoseconds()
    sr['attributes'] = {'str' : {'value' : 'derp'} }
    sr['type'] = 'Hurr'

    v = Version(sr)
    self.assertEqual(v.type(), 'Hurr')
    self.assertEqual(v.hash(), h1)
    self.assertEqual(v.parent(), h2)
    self.assertEqual(v.created(), now)
    self.assertEqual(v.committed(), now)
    self.assertEqual(v.shortHash(5), h1[0:5])
    self.assertEqual(v.attributeValue('str'), 'derp')
    self.assertEqual(v.attribute('str')['value'], 'derp')
    self.assertEqual(v['str']['value'], 'derp')
    self.assertEqual(hash(v), hash(h1))
    self.assertEqual(v, Version(sr))
    self.assertFalse(v.isBlank())

    self.assertRaises(KeyError, v.attribute, 'fdsafda')
    self.assertRaises(TypeError, cmp, v, 'fdsafda')

  def test_raises(self):

    sr = serial.SerialRepresentation()
    self.assertRaises(ValueError, Version, sr)
    sr['key'] = '/A'
    self.assertRaises(ValueError, Version, sr)
    sr['hash'] = 'a'
    self.assertRaises(ValueError, Version, sr)
    sr['parent'] = 'b'
    self.assertRaises(ValueError, Version, sr)
    sr['created'] = nanotime.now().nanoseconds()
    self.assertRaises(ValueError, Version, sr)
    sr['committed'] = 0
    self.assertRaises(ValueError, Version, sr)
    sr['committed'] = sr['created']
    self.assertRaises(ValueError, Version, sr)
    sr['attributes'] = {'str' : 'derp'}
    self.assertRaises(ValueError, Version, sr)
    sr['type'] = 'Hurr'
    Version(sr)


  def test_model(self):

    h1 = hashlib.sha1('derp').hexdigest()
    h2 = hashlib.sha1('herp').hexdigest()

    attrs = {'first' : {'value':'Herp'}, \
             'last' : {'value':'Derp'}, \
             'phone' : {'value': '123'}, \
             'age' : {'value': 19}, \
             'gender' : {'value' : 'Male'}}

    sr = serial.SerialRepresentation()
    sr['key'] = '/Person/PersonA'
    sr['hash'] = h1
    sr['parent'] = h2
    sr['created'] = nanotime.now().nanoseconds()
    sr['committed'] = sr['created']
    sr['attributes'] = attrs
    sr['type'] = 'Person'

    ver = Version(sr)
    instance = Person(ver)

    self.assertEqual(instance.__dstype__, ver.type())
    self.assertEqual(instance.version, ver)
    self.assertFalse(instance.isDirty())
    self.assertTrue(instance.isPersisted())
    self.assertTrue(instance.isCommitted())

    self.assertEqual(instance.key, Key('/Person/PersonA'))
    self.assertEqual(instance.first, 'Herp')
    self.assertEqual(instance.last, 'Derp')
    self.assertEqual(instance.phone, '123')
    self.assertEqual(instance.age, 19)
    self.assertEqual(instance.gender, 'Male')


class ModelTests(unittest.TestCase):

  def subtest_assert_uncommitted(self, instance):
    self.assertTrue(instance.created is None)
    self.assertTrue(instance.updated is None)
    self.assertTrue(instance.version.isBlank())

    self.assertTrue(instance.isDirty())
    self.assertFalse(instance.isPersisted())
    self.assertFalse(instance.isCommitted())

  def test_basic(self):
    a = Model('A')
    self.assertEqual(a.key, Key('/Model/A'))
    self.assertEqual(a.__dstype__, 'Model')
    self.assertEqual(Model.__dstype__, 'Model')
    self.subtest_assert_uncommitted(a)

    a.commit()
    created = a.version.created()

    print 'committed', a.version.hash()

    self.assertFalse(a.isDirty())
    self.assertTrue(a.isCommitted())
    self.assertEqual(a.version.type(), Model.__dstype__)
    self.assertEqual(a.version.hash(), a.computedHash())
    self.assertEqual(a.version.parent(), Version.BLANK_HASH)
    self.assertEqual(a.version.created(), created)

    a.commit()
    self.assertFalse(a.isDirty())
    self.assertTrue(a.isCommitted())
    self.assertEqual(a.version.type(), Model.__dstype__)
    self.assertEqual(a.version.hash(), a.computedHash())
    self.assertEqual(a.version.parent(), Version.BLANK_HASH)
    self.assertEqual(a.version.created(), created)

    a._isDirty = True
    self.assertTrue(a.isDirty())

    a.commit()
    self.assertFalse(a.isDirty())
    self.assertTrue(a.isCommitted())
    self.assertEqual(a.version.type(), Model.__dstype__)
    self.assertEqual(a.version.hash(), a.computedHash())
    self.assertEqual(a.version.parent(), Version.BLANK_HASH)
    self.assertEqual(a.version.created(), created)


  def test_attributes(self):
    p = Person('HerpDerp')
    self.assertEqual(p.key, Key('/Person/HerpDerp'))
    self.assertEqual(p.first, 'Firstname')
    self.assertEqual(p.last, 'Lastname')
    self.assertEqual(p.phone, 'N/A')
    self.assertEqual(p.age, 0)
    self.assertEqual(p.gender, None)

    self.subtest_assert_uncommitted(p)

    p.first = 'Herp'
    p.last = 'Derp'
    p.phone = '1235674444'
    p.age = 120

    p.commit()
    print 'committed', p.version.shortHash(8)

    self.assertFalse(p.isDirty())
    self.assertTrue(p.isCommitted())
    self.assertEqual(p.version.type(), Person.__dstype__)
    self.assertEqual(p.version.hash(), p.computedHash())
    self.assertEqual(p.version.parent(), Version.BLANK_HASH)

    self.assertEqual(p.first, 'Herp')
    self.assertEqual(p.last, 'Derp')
    self.assertEqual(p.phone, '1235674444')
    self.assertEqual(p.age, 120)
    self.assertEqual(p.gender, None)

    self.assertEqual(p.version.attributeValue('first'), 'Herp')
    self.assertEqual(p.version.attributeValue('last'), 'Derp')
    self.assertEqual(p.version.attributeValue('phone'), '1235674444')
    self.assertEqual(p.version.attributeValue('age'), 120)
    self.assertEqual(p.version.attributeValue('gender'), None)

    hash = p.version.hash()
    p.first = 'Herpington'
    p.gender = 'Troll'
    p.commit()
    print 'committed', p.version.shortHash(8)

    self.assertFalse(p.isDirty())
    self.assertTrue(p.isCommitted())
    self.assertEqual(p.version.type(), Person.__dstype__)
    self.assertEqual(p.version.hash(), p.computedHash())
    self.assertEqual(p.version.parent(), hash)

    self.assertEqual(p.first, 'Herpington')
    self.assertEqual(p.last, 'Derp')
    self.assertEqual(p.phone, '1235674444')
    self.assertEqual(p.age, 120)
    self.assertEqual(p.gender, 'Troll')

    self.assertEqual(p.version.attributeValue('first'), 'Herpington')
    self.assertEqual(p.version.attributeValue('last'), 'Derp')
    self.assertEqual(p.version.attributeValue('phone'), '1235674444')
    self.assertEqual(p.version.attributeValue('age'), 120)
    self.assertEqual(p.version.attributeValue('gender'), 'Troll')





class AttributeTests(unittest.TestCase):

  def subtest_attribute(self, attrtype, **kwds):
    error = lambda: Attribute(merge_strategy='bogus')
    self.assertRaises(TypeError, error)

    a = attrtype(name='a', **kwds)
    self.assertEqual(a.name, 'a')
    self.assertEqual(a._attr_name(), '_a')
    self.assertEqual(a.default, None)
    self.assertEqual(a.default_value(), None)
    self.assertFalse(a.required)
    self.assertTrue(isinstance(a.mergeStrategy, merge.MergeStrategy))

    # setup the binding to an object
    class Attributable(object):
      pass

    m = Attributable()
    m._attributes = {'a':a}
    a._attr_config(Attributable, 'a')

    self.assertEqual(a._attr_name(), '_a')
    self.assertEqual(m._attributes['a'], a)

    def testSet(value, testval=None):
      a.__set__(m, value)
      if not testval:
        testval = value
      self.assertEqual(a.__get__(m, object), testval)

    return testSet

  def test_attributes(self):
    test = self.subtest_attribute(Attribute)
    test(5, '5')
    test(5.2, '5.2')
    test(self, str(self))
    test('5')

    test = self.subtest_attribute(StringAttribute)
    test(5, '5')
    test(5.2, '5.2')
    test(self, str(self))
    test('5')
    self.assertRaises(ValueError, test, '5\n\n\nfdsijhfdiosahfdsajfdias')

    test = self.subtest_attribute(StringAttribute, multiline=True)
    test(5, '5')
    test(5.2, '5.2')
    test(self, str(self))
    test('5')
    test('5\n\n\nfdsijhfdiosahfdsajfdias')

    test = self.subtest_attribute(KeyAttribute)
    test(5, Key(5))
    test(5.2, Key(5.2))
    test(self, Key(self))
    test('5', Key('5'))
    self.assertRaises(ValueError, test, '5\n\n\nfdsijhfdiosahfdsajfdias')

    test = self.subtest_attribute(IntegerAttribute)
    test(5)
    test(5.2, 5)
    self.assertRaises(TypeError, test, self)
    test('5', 5)
    self.assertRaises(ValueError, test, '5a')

    test = self.subtest_attribute(TimeAttribute)
    test(5, nanotime.nanotime(5))
    test(5.2, nanotime.nanotime(5.2))
    self.assertRaises(TypeError, test, self)
    self.assertRaises(TypeError, test, '5')
    self.assertRaises(TypeError, test, '5a')
    test(nanotime.seconds(1000))





