
import unittest

from dronestore import datastore
from dronestore.model import Key, Model

from test_model import TestPerson

class TestDatastore(datastore.Datastore):

  def __init__(self):
    self._items = {}

  def get(self, key):
    '''Return the object named by key.'''
    try:
      return self._items[key]
    except KeyError, e:
      return None

  def put(self, key, value):
    '''Stores the object.'''
    if value is None:
      self.delete(key)
    else:
      self._items[key] = value

  def delete(self, key):
    '''Removes the object.'''
    try:
      del self._items[key]
    except KeyError, e:
      pass

  def contains(self, key):
    '''Returns whether the object is in this datastore.'''
    return key in self._items

  def __len__(self):
    return len(self._items)



class TestDatastoreClass(unittest.TestCase):


  def test_simple(self, stores=[], numelems=1000):

    def checkLength(len):
      try:
        for sn in stores:
          self.assertEqual(len(sn), numelems)
      except TypeError, e:
        pass

    if len(stores) == 0:
      s1 = TestDatastore()
      s2 = TestDatastore()
      s3 = TestDatastore()
      stores = [s1, s2, s3]

    pkey = Key('/dfadasfdsafdas/')

    checkLength(0)

    # insert numelems elems
    for value in range(0, numelems):
      key = pkey.child(value)
      for sn in stores:
        self.assertFalse(sn.contains(key))
        sn.put(key, value)
        self.assertTrue(sn.contains(key))
        self.assertEqual(sn.get(key), value)

    # reassure they're all there.
    checkLength(numelems)

    for value in range(0, numelems):
      key = pkey.child(value)
      for sn in stores:
        self.assertTrue(sn.contains(key))
        self.assertEqual(sn.get(key), value)

    checkLength(numelems)

    # change numelems elems
    for value in range(0, numelems):
      key = pkey.child(value)
      for sn in stores:
        self.assertTrue(sn.contains(key))
        sn.put(key, value + 1)
        self.assertTrue(sn.contains(key))
        self.assertNotEqual(value, sn.get(key))
        self.assertEqual(value + 1, sn.get(key))

    checkLength(numelems)

    # remove numelems elems
    for value in range(0, numelems):
      key = pkey.child(value)
      for sn in stores:
        self.assertTrue(sn.contains(key))
        sn.delete(key)
        self.assertFalse(sn.contains(key))

    checkLength(0)

  def test_tiered(self):

    s1 = TestDatastore()
    s2 = TestDatastore()
    s3 = TestDatastore()
    ts = datastore.TieredDatastore([s1, s2, s3])

    k1 = Key('1')
    k2 = Key('2')
    k3 = Key('3')

    s1.put(k1, '1')
    s2.put(k2, '2')
    s3.put(k3, '3')

    self.assertTrue(s1.contains(k1))
    self.assertFalse(s2.contains(k1))
    self.assertFalse(s3.contains(k1))
    self.assertTrue(ts.contains(k1))

    self.assertEqual(ts.get(k1), '1')
    self.assertEqual(s1.get(k1), '1')
    self.assertFalse(s2.contains(k1))
    self.assertFalse(s3.contains(k1))

    self.assertFalse(s1.contains(k2))
    self.assertTrue(s2.contains(k2))
    self.assertFalse(s3.contains(k2))
    self.assertTrue(ts.contains(k2))

    self.assertEqual(s2.get(k2), '2')
    self.assertFalse(s1.contains(k2))
    self.assertFalse(s3.contains(k2))

    self.assertEqual(ts.get(k2), '2')
    self.assertEqual(s1.get(k2), '2')
    self.assertEqual(s2.get(k2), '2')
    self.assertFalse(s3.contains(k2))

    self.assertFalse(s1.contains(k3))
    self.assertFalse(s2.contains(k3))
    self.assertTrue(s3.contains(k3))
    self.assertTrue(ts.contains(k3))

    self.assertEqual(s3.get(k3), '3')
    self.assertFalse(s1.contains(k3))
    self.assertFalse(s2.contains(k3))

    self.assertEqual(ts.get(k3), '3')
    self.assertEqual(s1.get(k3), '3')
    self.assertEqual(s2.get(k3), '3')
    self.assertEqual(s3.get(k3), '3')

    ts.delete(k1)
    ts.delete(k2)
    ts.delete(k3)

    self.assertFalse(ts.contains(k1))
    self.assertFalse(ts.contains(k2))
    self.assertFalse(ts.contains(k3))

    self.test_simple([ts])

  def test_sharded(self, numelems=1000):

    s1 = TestDatastore()
    s2 = TestDatastore()
    s3 = TestDatastore()
    s4 = TestDatastore()
    s5 = TestDatastore()
    stores = [s1, s2, s3, s4, s5]
    sharded = datastore.ShardedDatastore(stores)
    sumlens = lambda stores: sum(map(lambda s: len(s), stores))

    def checkFor(key, value, sharded, shard=None):
      correct_shard = sharded._stores[hash(key) % len(sharded._stores)]

      for s in sharded._stores:
        if shard and s == shard:
          self.assertTrue(s.contains(key))
          self.assertEqual(s.get(key), value)
        else:
          self.assertFalse(s.contains(key))

      if correct_shard == shard:
        self.assertTrue(sharded.contains(key))
        self.assertEqual(sharded.get(key), value)
      else:
        self.assertFalse(sharded.contains(key))

    self.assertEqual(sumlens(stores), 0)
    # test all correct.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded)
      shard.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for i in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      shard.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      sharded.put(key, value)
      checkFor(key, value, sharded, shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      shard = stores[hash(key) % len(stores)]
      checkFor(key, value, sharded, shard)
      if value % 2 == 0:
        shard.delete(key)
      else:
        sharded.delete(key)
      checkFor(key, value, sharded)
    self.assertEqual(sumlens(stores), 0)

    # try out adding it to the wrong shards.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded)
      incorrect_shard.put(key, value)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # ensure its in the same spots.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      incorrect_shard.put(key, value)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this wont do anything
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      sharded.delete(key)
      checkFor(key, value, sharded, incorrect_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this will place it correctly.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      incorrect_shard = stores[(hash(key) + 1) % len(stores)]
      correct_shard = stores[(hash(key)) % len(stores)]
      checkFor(key, value, sharded, incorrect_shard)
      sharded.put(key, value)
      incorrect_shard.delete(key)
      checkFor(key, value, sharded, correct_shard)
    self.assertEqual(sumlens(stores), numelems)

    # this will place it correctly.
    for value in range(0, numelems):
      key = Key('/fdasfdfdsafdsafdsa/%d' % value)
      correct_shard = stores[(hash(key)) % len(stores)]
      checkFor(key, value, sharded, correct_shard)
      sharded.delete(key)
      checkFor(key, value, sharded)
    self.assertEqual(sumlens(stores), 0)

    self.test_simple([sharded])


  def test_lru(self):

    from dronestore.datastore import lrucache

    lru1 = lrucache.LRUCache(1000)
    lru2 = lrucache.LRUCache(2000)
    lru3 = lrucache.LRUCache(3000)
    lrus = [lru1, lru2, lru3]

    for value in range(0, 3000):
      key = Key('/LRU/%d' % value)
      for lru in lrus:
        self.assertFalse(lru.contains(key))

        lru.put(key, value)

        self.assertTrue(lru.contains(key))
        self.assertEqual(lru.get(key), value)

    self.assertEqual(len(lru1), 1000)
    self.assertEqual(len(lru2), 2000)
    self.assertEqual(len(lru3), 3000)

    for value in range(0, 3000):
      key = Key('/LRU/%d' % value)
      self.assertEqual(lru1.contains(key), value >= 2000)
      self.assertEqual(lru2.contains(key), value >= 1000)
      self.assertTrue(lru3.contains(key))

    lru1.clear()
    lru2.clear()
    lru3.clear()

    self.assertEqual(len(lru1), 0)
    self.assertEqual(len(lru2), 0)
    self.assertEqual(len(lru3), 0)

    self.test_simple(lrus)


  def test_mongo(self):

    import os
    import sys
    sys.path.append('/Users/jbenet/git/mongo/pymongo')

    from dronestore.datastore import mongo
    import pymongo

    conn = pymongo.Connection()
    conn.drop_database('dronestore_datastore_testdb')

    try:
      ms = mongo.MongoDatastore(conn.dronestore_datastore_testdb.testcollection)
      self.test_simple([ms], numelems=100)
    finally:
      conn.drop_database('dronestore_datastore_testdb')
