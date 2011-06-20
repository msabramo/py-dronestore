
from model import Key, Version, Model
from datastore import Datastore
from util.serial import SerialRepresentation

import merge

#THINKME(jbenet): consider moving the interface to ONLY take versions as input
#                 and output, rather than full-fledged models.
#        Problem: hanging on to pointers to object can be
#                 dangerous as Drones can merge them or the client can clobber
#                 them.
#       Benefits: This also alows the Drone to be truly a Version repository,
#                 and store only state without having to make logical sense.
#      Drawbacks: The overhead of (de)serializing from versions every op.


class Drone(object):
  '''Drone represents the logical unit of storage in dronestore.
  Each drone consists of a datastore (or set of datastores) and an id.
  '''

  def __init__(self, droneid, store):
    '''Initializes drone with given id and datastore.'''
    if not isinstance(droneid, Key):
      droneid = Key(droneid)
    if not isinstance(store, Datastore):
      raise ValueError('store must be an instance of %s' % Datastore)

    self._droneid = droneid
    self._store = store

  @property
  def droneid(self):
    '''This drone's identifier.'''
    return self._droneid

  @classmethod
  def _cleanVersion(cls, parameter):
    '''Extracts the version from input.'''
    if isinstance(parameter, Version):
      return parameter
    elif isinstance(parameter, Model):
      if parameter.isDirty():
        raise ValueError('cannot store entities with uncommitted changes')
      return parameter.version

    raise TypeError('expected input of type %s or %s' % (Version, Model))


  def put(self, versionOrEntity):
    '''Stores the current version of `entity` in the datastore.'''
    version = self._cleanVersion(versionOrEntity)
    self._store.put(version.key(), version.serialRepresentation().data())

  def get(self, key):
    '''Retrieves the current entity addressed by `key`'''
    if not isinstance(key, Key):
      raise ValueError('key must be of type %s' % Key)

    # lookup the key in the datastore
    data = self._store.get(key)
    if data is None:
      return data

    # handle the data. if any conversion fails, propagate the exception up.
    serialRep = SerialRepresentation(data)
    version = Version(serialRep)
    return Model.from_version(version)

  def merge(self, newVersionOrEntity):
    '''Merges a new version of an instance with the current one in the store.'''

    # get the new version
    new_version = self._cleanVersion(newVersionOrEntity)

    # get the instance
    key = new_version.key()
    curr_instance = self.get(key) #THINKME(jbenet): try contains first?
    if curr_instance is None:
      raise KeyError('no entity found with key %s' % key)

    # NOTE: semantically, we must merge into the current instance in the drone
    # so that merge strategies favor the incumbent version.

    merge.merge(curr_instance, new_version)

    # store it back
    self.put(curr_instance)
    return curr_instance

  def delete(self, key):
    '''Deletes the entity addressed by `key` from the datastore.'''
    if not isinstance(key, Key):
      raise ValueError('key must be of type %s' % Key)

    self._store.delete(key)

