

def merge(instance, version):
  if instance.isDirty():
    raise MergeFailure('Cannot merge dirty instance.')

  merge_values = {}
  for attr in instance.attributes().values():
    value = attr.mergeStrategy.merge(instance.version(), version)
    if value: # none value means no change, i.e. keep the local attribute.
      merge_values[attr.name] = value

  # merging checks out, actually make the changes.
  for attrname, value in merge_values.iteritems():
    setattr(instance, attrname, value)

  instance.commit()


class MergeDirection:
  '''MergeDirection represents an enumeration to identify which side to keep.'''
  Local, Remote, Merge = range(1,4)

class MergeStrategy(object):
  '''A MergeStrategy represents a unique way to decide how the two values of a
  particular attributes merge together.

  MergeStrategies are meant to enforce a particular rule that helps ensure
  application semantics regarding attributes changed in multiple nodes.

  MergeStrategies can store state in the object (e.g. a timestamp). If so,
  MergeStrategies must set the REQUIRES_STATE class variable to True.
  '''

  REQUIRES_STATE = False


  def __init__(self, attribute):
    self.attribute = attribute

  def merge(self, local_version, remote_version):
    raise NotImplementedError('No implementation for %s.merge()', \
      self.__class__.__name__)





class LatestObjectStrategy(MergeStrategy):
  '''LatestObjectStrategy merges attributes based solely on objects' timestamp.
  In essence, the most recently written object wins.

  This Strategy stores no additional state.
  '''

  def merge(self, local_version, remote_version):
    if remote_version.committed() > local_version.committed():
      return remote_version.attribute(self.attribute.name)
    return None





class LatestAttributeStrategy(MergeStrategy):
  '''LatestStrategy merges attributes based solely on timestamp. In essence, the
  most recently written attribute wins.

  This Strategy stores its state like so:
  { 'updated' : nanotime.NanoTime, 'value': attrValue }

  A value with a timestamp will be preferred over values without.
  '''

  REQUIRES_STATE = True

  def merge(self, local_version, remote_version):
    attr_name = self.attribute.name
    attr_local = local_version.attribute(attr_name)
    attr_remote = remote_version.attribute(attr_name)

    # if no timestamp found in remote. we're done!
    if 'updated' not in attr_remote:
      return None

    # since other side has a timestamp, if we don't, take theirs.
    if 'updated' not in attr_local:
      return attr_remote

    # if we havent decided (both have timestamps), compare timestamps
    if attr_remote['updated'] > attr_local['updated']:
      return attr_remote
    return None # no change. keep local





class MaxStrategy(MergeStrategy):
  '''MaxStrategy merges attributes based solely on comparison. In essence, the
  larger value is picked.

  This Strategy stores no additional state.

  A value with a timestamp will be preferred over values without.
  '''

  def merge(self, local_version, remote_version):
    attr_name = self.attribute.name
    attr_local = local_version.attribute(attr_name)
    attr_remote = remote_version.attribute(attr_name)

    if attr_remote > attr_local:
      return attr_remote
    return None # no change. keep local



