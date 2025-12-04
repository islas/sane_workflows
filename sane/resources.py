from abc import abstractmethod
import re
import datetime
import math
import operator
import copy
from typing import Dict, List

import sane.logger as logger
import sane.json_config as jconfig
import sane.config as config
from sane.helpers import copydoc

# Format using PBS-stye
# http://docs.adaptivecomputing.com/torque/4-1-3/Content/topics/2-jobs/requestingRes.htm
_res_size_regex_str = r"^(?P<numeric>-?\d+)(?P<multi>(?P<scale>k|m|g|t)?(?P<unit>b|w)?)$"
_res_size_regex     = re.compile( _res_size_regex_str, re.I )
_multipliers    = { "" : 1, "k" : 1024, "m" : 1024**2, "g" : 1024**3, "t" : 1024**4 }

_timelimit_regex_str    = r"^(?P<hh>\d+):(?P<mm>\d+):(?P<ss>\d+)$"
_timelimit_regex        = re.compile( _timelimit_regex_str )
_timelimit_format_str   = "{:02}:{:02}:{:02}"


class Resource:
  """A quantifiable positive integer resource

  :py:class:`Resource` is a wrapper class on quatifiable values to facilitate common
  operations such as basic arithmetic, reduction to human-readable scaled units (in
  binary metric prefix, e.g. kibi, mebi, etc.), and type-checking operations between
  matching resource types or scalars.

  :py:attr:`Resource.amount` can be set to anything that follows the following
  regular expression:

  | ``(\\d+)(k|m|g|t)?(b|w)?``

  | The first capture group (1st set of parenthesis) expects any number of numeric literals.
  | The second capture group (2nd set of parenthesis) optionally can be a binary scale
  | The third capture group (3rd set of parenthesis) optionally can be a unit (limited to 'b' or 'w' currently)

  Examples of valid and invalid resource amounts:

  .. code-block:: python

      # valid
      1
      8k
      512mb

      # invalid
      1.0
      -2
      7.6gw

  All supported binary operations on a :py:class:`Resource` return a new :py:class:`Resource`
  with the resultant :py:attr:`amount` *except* the division of two resources which results
  in an ``int`` value. The following operations are supported:

  .. code-block:: python

      res_a = sane.resource.Resource( "mem", "4gb" )
      res_b = sane.resource.Resource( "mem", "2gb" )
      # addition and subtraction
      res_a + res_b or res_a - res_b
      res_a + 12345 or res_a - 12345
      # multiplication and division
      res_a * 2 or res_a / 2
                   res_a / res_b # Note: This results in an int and mult is not supported

      res_c = sane.resource.Resource( "cpus", 12 )
      # Unsupported operations
      res_a + res_c         # incompatible resouce type
      res_a + 1.2345        # float add/sub
      res_a - 1.2345        # float add/sub
      res_a * res_b         # undefined behavior
      res_a - ( res_a * 2 ) # negative amount not allowed

  .. note:: :py:attr:`Resource.amount` must be an integer value, even if scaled.
            The :py:attr:`total` or :py:attr:`current` values will always be integer
            values, even if unscaled or multiplied/divided by a ``float`` value.

  Scaling amounts:

  ====== =============
  prefix multiplier
  ====== =============
  ``k``  1024
  ``m``  1024 :sup:`2`
  ``g``  1024 :sup:`3`
  ``t``  1024 :sup:`4`
  ====== =============
  """
  def __init__( self, resource : str, amount=0, unit="" ):
    """Create a :py:class:`Resource` with type ``resource``
    
    :param resource: Set the type of the resource. Resources of different types cannot interoperate.
    :param amount:   Set the :py:attr:`amount` that this resource is. See class summary for valid syntax.
    :param unit:     If set, overrides the detected unit (if any) passed in via ``amount``
    """
    self._resource = resource
    self._original_amount = None
    self._res_dict = None
    self.amount = amount
    if unit != "":
      self._res_dict["unit"] = unit

  @staticmethod
  def is_resource( potential_resource ):
    """Check if the input value (``str`` or ``int``) follows valid :py:class:`Resource.amount` syntax"""
    res_dict = res_size_dict( potential_resource )
    return res_dict is not None

  @property
  def resource( self ):
    """The type of this resource"""
    return self._resource

  @property
  def unit( self ):
    """The unit of this resource"""
    return self._res_dict["unit"]

  @property
  def amount( self ):
    """The original amount of this resource

    :param amount: If set, changes this resources :py:attr:`amount` entirely,
                   but not the :py:attr:`resource` type.
    """
    return self._original_amount

  @amount.setter
  def amount( self, amount ):
    # Caution, this resets everything
    self._original_amount = amount
    self._res_dict = res_size_expand( res_size_dict( amount ) )
    self._check_bounds()

  @property
  def total( self ) -> int:
    """The total unscaled (expanded) numeric value"""
    return self._res_dict["numeric"]

  @property
  def current( self ) -> int:
    """The :py:attr:`total`"""
    return self.total

  @current.setter
  def current( self, amount ):
    self.amount = amount
    self._check_bounds()

  # These are always reduced
  @property
  def total_str( self ):
    """The :py:attr:`total` scaled (reduced) value, including units"""
    return res_size_str( res_size_reduce( self._res_dict ) )

  @property
  def current_str( self ):
    """The :py:attr:`current` scaled (reduced) value, including units"""
    res_dict = self._res_dict.copy()
    res_dict["numeric"] = self.current
    return res_size_str( res_size_reduce( res_dict ) )

  def _raise_op_err( self, op, operand ):
    raise TypeError( f"unsupported operand types(s) for {op}: '{type(self).__name__}' and '{type(operand).__name__}'" )

  def _check_bounds( self ):
    if self._res_dict is None:
      raise TypeError( "resource is not a valid numeric resource" )
    if self.total < 0:
      raise ValueError( "resource total cannot be negative" )

  def _check_operable( self, op, operand, valid_types ):
    if not isinstance( operand, valid_types ):
      self._raise_op_err( op, operand )
    if isinstance( operand, Resource ):
      if operand.unit != self.unit:
        raise TypeError( f"operand resource units do not match: '{self.unit}' and '{operand.unit}'" )
      if operand.resource != self.resource:
        raise TypeError( f"operand resource types do not match: '{self.resource}' and '{operand.resource}'" )

  def _operate( self, op, operand ):
    if isinstance( operand, Resource ):
      return op( self.current, operand.current )
    else:
      return op( self.current, operand )

  def _construct_result( self, amount ):
    result = copy.deepcopy( self )
    result.current = f"{amount}{result.unit}"
    return result

  def __add__( self, resource ):
    self._check_operable( "+", resource, ( int, Resource ) )
    amount = self._operate( operator.add, resource )
    return self._construct_result( amount )

  def __sub__( self, resource ):
    self._check_operable( "-", resource, ( int, Resource ) )
    amount = self._operate( operator.sub, resource )
    return self._construct_result( amount )

  def __mul__( self, resource ):
    self._check_operable( "*", resource, ( int, float ) )
    amount = math.ceil( self._operate( operator.mul, resource ) )
    return self._construct_result( amount )

  def __truediv__( self, resource ):
    self._check_operable( "*", resource, ( int, float, Resource ) )
    amount = math.ceil( self._operate( operator.truediv, resource ) )
    if isinstance( resource, Resource ):
      return int( amount )
    else:
      return self._construct_result( amount )

  def __iadd__( self, resource ):
    res = self.__add__( resource )
    self.current = res.current
    return self

  def __isub__( self, resource ):
    res = self.__sub__( resource )
    self.current = res.current
    return self

  def __imul__( self, resource ):
    res = self.__mul__( resource )
    self.current = res.current
    return self

  def __itruedvi__( self, resource ):
    self._check_operable( "/=", resource, ( int, float ) )
    res = self.__truediv__( resource )
    self.current = res.current
    return self

  def __repr__( self ):
    return self.current_str


class AcquirableResource( Resource ):
  """A :py:class:`Resource` that also tracks the amount acquired internally

  This class internally contains another :py:class:`Resource` that tracks the
  acquirable amount of the resouce. The original acquirable amount always matches
  the :py:attr:`amount` set at instantiation, and setting :py:attr:`amount`
  afterwards results in undefined behavior.

  All supported binary operations on an :py:class:`AcquirableResource` return a
  new :py:class:`AcquirableResource` and operate on the underlying :py:attr:`acquirable`
  amount. The :py:attr:`AcquirableResource.amount` is unaffected.

  For example:

  .. code-block:: python

      res_a = sane.resource.Resource( "mem", "4gb" )
      res_b = sane.resource.Resource( "mem", "1gb" )

      res_c = res_a - res_b
      res_c.current_str # outputs "3gb"
      res_c.total_str   # outputs the original "4gb"
  """
  def __init__( self, resource, amount ):
    #: The underlying :py:class:`Resource` tracking the amount of resource currently acquirable
    self.acquirable = Resource( resource, amount )
    super().__init__( resource=resource, amount=amount )

  def _check_bounds( self ):
    if self.acquirable.current < 0:
      raise ValueError( "acquirable resource amount cannot go below zero" )
    if self.acquirable.current > self.total:
      raise ValueError( "acquirable resource amount cannot go above total" )
    super()._check_bounds()

  @property
  def current( self ):
    """The current :py:attr:`acquirable` :py:attr:`~Resource.amount`

    :param amount: If set, changes the :py:attr:`acquirable.amount <Resource.amount>`
                   to this value.
    """
    return self.acquirable.current

  @current.setter
  def current( self, amount ):
    self.acquirable.current = amount
    self._check_bounds()

  @property
  def used( self ):
    """The total used amount of resources, :py:attr:`total` - :py:attr:`acquirable.total <Resource.total>`"""
    return self.total - self.acquirable.total

  @property
  def used_str( self ):
    """The :py:attr:`used` scaled (reduced) value, including units"""
    res_dict = self._res_dict.copy()
    res_dict["numeric"] = self.used
    return res_size_str( res_size_reduce( res_dict ) )

  def __repr__( self ):
    return f"{{ total: {self.total_str}, used: {self.used_str} }}"


def res_size_dict( resource ) :
  match = _res_size_regex.match( str( resource ) )
  res_dict = None
  if match is not None :
    res_dict = { k : ( v.lower() if v is not None else "" ) for k, v in match.groupdict().items() }
    res_dict["numeric"] = int(res_dict["numeric"])
    return res_dict
  else :
    return None


def res_size_base( res_dict ) :
  return _multipliers[ res_dict["scale" ] ] * res_dict["numeric"]


def res_size_str( res_dict ) :
  size_fmt = "{num}{scale}{unit}"
  return size_fmt.format(
                          num=res_dict["numeric"],
                          scale=res_dict[ "scale" ] if res_dict[ "scale" ] else "",
                          unit=res_dict["unit"]
                          )


def res_size_expand( res_dict ) :
  if res_dict is None:
    return None

  expanded_dict = {
                    "numeric" : _multipliers[ res_dict["scale" ] ] * res_dict["numeric"],
                    "scale" : "",
                    "unit" : res_dict["unit"]
                  }
  return expanded_dict


def res_size_reduce( res_dict ) :
  total = res_size_base( res_dict )

  # Convert to simplified size, round up if needed
  log2 = -1.0
  if res_dict["numeric"] > 0:
    log2 = math.log( total, 2 )
  scale = ""
  if log2 > 30.0 :
    # Do it in gibi
    scale = "g"
  elif log2 > 20.0 :
    # mebi
    scale = "m"
  elif log2 > 10.0 :
    # kibi
    scale = "k"

  reduced_dict = {
                    "numeric" : math.ceil( total / float( _multipliers[ scale ] ) ),
                    "scale"   : scale,
                    "unit"    : res_dict["unit"]
                  }
  return reduced_dict


def timelimit_to_timedelta( timelimit ) :
  time_match = _timelimit_regex.match( timelimit )
  if time_match is not None :
    groups = time_match.groupdict()
    return timedelta(
                      hours=int( groups["hh"] ),
                      minutes=int( groups["mm"] ),
                      seconds=int( groups["ss"] )
                    )
  else :
    return None


def timedelta_to_timelimit( timedelta ) :
  totalSeconds = timelimit.total_seconds()
  return '{:02}:{:02}:{:02}'.format(
                                    int( totalSeconds // 3600 ),
                                    int( totalSeconds % 3600 // 60 ),
                                    int( totalSeconds % 60 )
                                    )


class ResourceMatch( config.Config ):
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )

  def match( self, requested_resource ):
    return self.exact_match( requested_resource )


class ResourceMapper(  ):
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    self._mapping = {}

  @property
  def num_maps( self ):
    return len( self._mapping )

  def add_mapping( self, resource : str, aliases : List[str] ):
    """Add a mapping of ``resource`` name to a list of ``aliases``

    :param list[str] aliases: A set of aliases to associate this ``resource name with.
    """
    self._mapping[resource] = ResourceMatch( name=resource, aliases=aliases )

  def name( self, resource : str ) -> str:
    for resource_name, resource_match in self._mapping.items():
      if resource_match.match( resource ):
        return resource_name
    return resource


class ResourceRequestor( jconfig.JSONConfig ):
  """Aggregates any arbitrary resource requests to be made to a :py:class:`ResourceProvider`
  
  .. note:: Resources listed here are stored verbatim and thus can be anything.
            The onus of allocation of resources is left to the :py:class:`ResourceProvider`
            implementation. The default classes only support resources that would
            match the :py:class:`Resource` syntax.
  """
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    self._resources            = {}
    self._override_resources   = {}

    #: Control if the resources requested should be provided from a local pool
    #: if a :py:class:`NonLocalProvider` is used. If set to ``None`` then resource
    #: delegation is left to the provider, ``True`` to force local, and ``False``
    #: to force non-local. If the provider is a normal :py:class:`ResourceProvider`
    #: this option has no effect.
    self.local = None

  def resources( self, override : str = None ) -> dict:
    """Return a copy of the current resources requested

    During workflow execution, the :py:attr:`~Orchestrator.current_host` will be
    provided as the ``override`` value when requesting resources from the
    :py:class:`Host` via :py:meth:`ResourceProvider.acquire_resources()`

    :param override: If an override ``dict`` exists in the resources, return a
                     copy of the resources recursively updated to prioritize the
                     overriden values.
    """
    resource_dict = self._resources.copy()
    if override is not None:
      for override_key in self._override_resources.keys():
        # Allow partial match
        if override_key in override:
          jconfig.recursive_update( resource_dict, self._override_resources[override_key] )
          break
    return resource_dict

  def add_resource_requirements( self, resource_dict : dict ):
    """Add resource requirements to this requestor

    .. hint:: See :py:class:`Resource` for syntax on default supported values

    Add an arbitrary dict of key-value pairs to this requestor. The key-value pairs
    in this dict will eventually be requested from a :py:class:`ResourceRequestor`
    for:
      
      * :py:meth:`~ResourceRequestor.acquire_resources()`
      * :py:meth:`~ResourceRequestor.release_resources()`
      * :py:meth:`~ResourceRequestor.resources_available()`

    If the value in a key-value pair is of type ``dict``, it will be considered
    an override resource request specific to the name of the key. This override
    ``dict`` will be kept separately in an internal location to be used later.
    Multiple nested ``dict`` overrides are not allowed.

    See :py:meth:`resources()` for more info.

    As an example:

    .. code-block:: python

        {
          "cpus"  : 12,
          "mem"   : "1gb",
          "slots" : 1
          "specific_provider" :
          {
            "cpus" : 36,
            "mem"  : "3gb"
          }
        }

    The values of ``"specific_provider"`` will only be used (in addition to any
    unmodified values in the top-level dict) if the :py:attr:`~Orchestrator.current_host`
    matches this key.

    .. note:: While the ``resource_dict`` can be arbitrary values, it is on the
              :py:class:`ResourceProvider` (i.e. :py:class:`Host`) to be able to
              provide these resources. 
              
              Notably, any resources that do not follow the :py:class:`Resource`
              syntax are left strictly to the provider class implementation. The
              default classes do not support values outside of :py:class:`Resource`
              unless specified.

    """
    for resource, info in resource_dict.items():
      if resource in self._resources:
        self.log( f"Resource '{resource}' already set, ignoring new resource setting", level=30 )
      else:
        if isinstance( info, dict ):
          if resource not in self._override_resources:
            self._override_resources[resource] = {}
          for override, override_info in info.items():
            if override in self._override_resources[resource]:
              self.log( f"Resource '{override}' already set in {resource}, ignoring new resource setting", level=30 )
            else:
              self._override_resources[resource][override] = override_info
        else:
          self._resources[resource] = info

  @copydoc( jconfig.JSONConfig.load_core_config, append=False )
  def load_core_config( self, config : dict, origin : str ):
    """Load :py:class:`ResourceRequestor` resource requirements

    The following key is loaded verbatim into :py:meth:`add_resource_requirments`:

    * ``"resources"``

    The following key is loaded if possible, defaulting to ``None``:

    * ``"local"`` => :py:attr:`local`
    """
    self.add_resource_requirements( config.pop( "resources", {} ) )

    local = config.pop( "local", None )
    if local is not None:
      self.local = local

    super().load_core_config( config, origin )


class ResourceProvider( jconfig.JSONConfig ):
  """Manages and provides use of :py:class:`AcquirableResources <AcquirableResource>`

  During workflow execution the :py:class:`ResourceProvider` will be given the
  :py:attr:`~ResourceRequestor.resources` of each runnable :py:class:`ResourceRequestor`
  (``Action``) to check for availability, acquire, and finally release the
  :py:attr:`~ResourceRequestor.resources` at completion.
  """
  def __init__( self, mapper=None, **kwargs ):
    super().__init__( **kwargs )
    self._resources    = {}
    if mapper is None:
      self._mapper = ResourceMapper()
    else:
      self._mapper = mapper
    self._resource_log = {}

  @property
  def resources( self ) -> Dict[str, AcquirableResource]:
    """A copy of the available resources

    :return: a deep copy of the internal resources in their current state
    :rtype: dict[str, AcquirableResource]
    """
    return copy.deepcopy( self._resources )

  def add_resources( self, resource_dict : dict, override=False ):
    """Add resources to this provider that can be acquired

    .. hint:: See :py:class:`Resource` for syntax on default supported values

    Add a dict of key-value pairs to this provider. The key-value pairs in this
    dict will be used to create :py:class:`AcquirabeResource` instances that track
    resource requests from a :py:class:`ResourceRequestor`.

    As an example:

    .. code-block:: python

        {
          "cpus"  : 12,
          "mem"   : "1gb",
          "slots" : 2
        }

    The above ``resource_dict`` would provide 12 counts of ``"cpus"``, 1024 :sup:`3`
    ``b`` units of ``"mem"``, and 2 counts of ``"slots"``. 
    
    .. important:: The :py:class:`ResourceProvider` has no inherent understanding
                   of the units, amounts, or names of resources. Internally, resources
                   will be tracked but at acquisition these resources will not
                   correspond to any form of real hardware / software allocations
                   or locks unless logic within a custom implementation of a derived
                   :py:class:`ResourceProvider` specifies.
    """
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    for resource, info in mapped_resource_dict.items():
      if not Resource.is_resource( info ):
        self.log( f"Skipping resource '{resource}', is non-numeric: '{info}'", level=10 )
        continue

      if not override and resource in self._resources and self._resources[resource].total > 0:
        self.log( f"Resource ''{resource}'' already set, ignoring new resource setting", level=30 )
      else:
        self._resources[resource] = AcquirableResource( resource, info )
        self._resource_log[resource] = { "acquire" : [], "release" : [], "unit" : self._resources[resource].unit }

  def resources_available( self, resource_dict : dict, requestor : ResourceRequestor, log=True ) -> bool:
    """Check if the all resources in the requested ``resource_dict`` are currently available"""
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    origin_msg = f" for '{requestor.logname}'"

    if log:
      self.log( f"Checking if resources available{origin_msg}...", level=10 )
      self.log_push()
    can_aquire = True
    for resource, info in mapped_resource_dict.items():
      res = None
      if isinstance( info, Resource ):
        res = info
      elif Resource.is_resource( info ):
        if resource not in self._resources:
          msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
          msg += "host does not possess this resource. "
          msg += f"Resources: {self.resources}"
          self.log( msg, level=50 )
          self.log_pop()
          raise Exception( msg )
        else:
          res = Resource( resource, info, unit=self._resources[resource].unit )
      else:
        self.log( f"Skipping resource '{resource}', is non-numeric: '{info}'", level=10 )
        continue

      if res.total > self._resources[resource].total:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "requested amount is greater than available total " + self._resources[resource].total_str
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      acquirable = res.total <= self._resources[resource].current
      if not acquirable and log:
        self.log( f"Resource '{resource}' : {res.total_str} not acquirable right now ({self._resources[resource]})...", level=10 )
      can_aquire = can_aquire and acquirable

    if log:
      if can_aquire:
        self.log( f"All resources{origin_msg} available", level=10 )
      else:
        self.log( f"Not all resources available", level=10 )
      self.log_pop()
    return can_aquire

  def acquire_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    """Acquire all the resources in the ``resource_dict``"""
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    origin_msg = f" for '{requestor.logname}'"

    self.log( f"Acquiring resources{origin_msg}...", level=10 )
    self.log_push()
    if self.resources_available( mapped_resource_dict, requestor ):
      for resource, info in mapped_resource_dict.items():
        res = None
        if isinstance( info, Resource ):
          res = info
        elif Resource.is_resource( info ):
          res = Resource( resource, info, unit=self._resources[resource].unit )
        else:
          continue
        self.log( f"Acquiring resource '{resource}' : {res.total_str}", level=10 )
        self._resources[resource] -= res
        now = datetime.datetime.now().isoformat()
        self._resource_log[resource]["acquire"].append( [ requestor.logname, res.total, now, self._resources[resource].used ] )
    else:
      self.log( f"Could not acquire resources{origin_msg}", level=10 )
      self.log_pop()
      return False

    self.log_pop()
    return True

  def release_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    """Release all the resources in the ``resources_dict``"""
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    origin_msg = f" from '{requestor.logname}'"

    self.log( f"Releasing resources{origin_msg}...", level=10 )
    self.log_push()
    for resource, info in mapped_resource_dict.items():
      res = None
      if isinstance( info, Resource ):
        res = info
      elif Resource.is_resource( info ):
        res = Resource( resource, info, unit=self._resources[resource].unit )
      else:
        continue

      if resource not in self._resources:
        self.log( f"Cannot return resource '{resource}', instance does not possess this resource", level=30 )

      if res.total > self._resources[resource].used:
        msg  = f"Cannot return resource '{resource}' : {res.total_str}, "
        msg += "amount is greater than current in use " + self._resources[resource].used_str
        self.log( msg, level=30 )
      else:
        self.log( f"Releasing resource '{resource}' : {res.total_str}", level=10 )
        self._resources[resource] += res
        now = datetime.datetime.now().isoformat()
        self._resource_log[resource]["release"].append( [ requestor.logname, res.total, now, self._resources[resource].used ] )
    self.log_pop()

  @copydoc( jconfig.JSONConfig.load_core_config, append=False )
  def load_core_config( self, config, origin ):
    """Load the available resources for this :py:class:`ResourceProvider`

    The following key is loaded verbatim into :py:meth:`add_resources`:

    * ``"resources"``

    The following key is loaded into the internal :py:attr:`_mapper` as a ``dict[str,list[str]]``
    via :py:meth:`ResourceMapper.add_mapping`, where each key in the ``dict`` is
    a resource name/type and the value is a list of strings to use as aliases:

    * ``"mapping"``

    An example config:

    .. code-block:: python

      {
        "resources" :
        {
          "cpus" : 123,
          "mem"  : "64mb",
        }
        "mapping" : 
        {
          "ncpus" : [ "cpus", "cpu", "procs", "proc", "processors" ]
        }
      }

    The above ``config`` would provide map ``"cpus"`` to ``"ncpus"`` and add an
    :py:class:`AcquirableResource` of type ``"ncpus"`` with amount 123 and an
    :py:class:`AcquirableResource` of type ``"mem"`` with amount 64mb to the
    :py:attr:`resources`.

    .. note:: When using a mapping, the :py:class:`ResourceRequestor` and :py:class:`ResourceProvider`
              can use any of the alias names or map key itself in its ``resources``.
              Within the :py:class:`ResourceProvider`, all ``resources`` will always
              be internally mapped to the corresponding map key if available.

              This allows the creation of :py:class:`ResourceRequestor` and :py:class:`ResourceProvider`
              that for one reason or another wish to refer to the same resources
              by different names.
    """
    resources = config.pop( "resources", {} )
    if len( resources ) > 0:
      self.add_resources( resources )

    mapping = config.pop( "mapping", {} )
    for resource, aliases in mapping.items():
      self._mapper.add_mapping( resource, aliases )

    super().load_core_config( config, origin )

  def map_resource( self, resource : str ) -> str:
    """Map the input ``resource`` to an internal name, if available
    
    If the resource has no internal mapping, the original ``resource`` is returned.

    :return: the ``resource`` name using the map key
    """
    mapped_resource = self._mapper.name( resource )
    res_split = resource.split( ":" )
    if len( res_split ) == 2:
      mapped_resource = "{0}:{1}".format( self._mapper.name( res_split[0] ), res_split[1] )
    return mapped_resource

  def map_resource_dict( self, resource_dict : dict, log=False ) -> dict:
    """Map entire dict to internal names
    
    For each resource entry in the ``resource_dict`` attempt to :py:meth:`map_resource`,
    and return a copy of the dict using any updated mapped keys instead. If no
    resources have mappings, then a verbatim copy is returned.

    :return: a copy of ``resource_dict`` using mapped resource
             names where appicable instead.
    """
    output_log = ( log and self._mapper.num_maps > 0 )
    if output_log:
      self.log( "Mapping resources with internal names..." )
      self.log_push()
    mapped_resource_dict = resource_dict.copy()
    for resource in resource_dict:
      mapped_resource = self.map_resource( resource )

      if mapped_resource != resource:
        if output_log:
          self.log( f"Mapping {resource} to internal name {mapped_resource}" )
        mapped_resource_dict[mapped_resource] = resource_dict[resource]
        del mapped_resource_dict[resource]
    if output_log:
      self.log_pop()
    return mapped_resource_dict

  @property
  def resource_log( self ):
    return self._resource_log


class NonLocalProvider( ResourceProvider ):
  """An abstract base class specialization of :py:class:`ResourceProvider`
  
  This class introduces the concept of a "local" pool of resources separate from
  the rest of the :py:attr:`resources` this provider offers. This nomenclature
  suggests that all :py:attr:`resources` directly in this class (not in the
  :py:attr:`local_resources`) are thus nonlocal.
  
  The internal local pool is itself a :py:class:`ResourceProvider`.
  The local pool and this instance share a common :py:class:`ResourceMapper`.
  """
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    #: Set whether :py:class:`ResourceRequestor` with
    #: :py:attr:`~Resourcerequestor.local` set to ``None``
    #: should default to using :py:attr:`local_resource`
    self.default_local = False
    #: Set to force all :py:class:`ResourceRequestor` to
    #: acquire from :py:attr:`local_resources`, regardless
    #: of :py:attr:`ResourceRequestor.local` setting
    self.force_local = False
    #: An internal :py:class:`ResourceProvider` to
    #: manage local resource requests
    self.local_resources = ResourceProvider( mapper=self._mapper, logname=f"{self.logname}::local" )

  @copydoc( jconfig.JSONConfig.load_core_config, append=False )
  @copydoc( ResourceProvider.load_core_config )
  def load_core_config( self, config, origin ):
    """Load local resources into :py:attr:`local_resources` and control flags
    
    The following key is loaded verbatim into :py:attr:`local_resources` via
    :py:meth:`ResourceProvider.add_resources`:

    * ``"local_resources"``

    The following keys are loaded, if available, into their respective attribute.
    If not present, the attributes are unmodified:

    * ``"default_local"`` => :py:attr:`default_local`
    * ``"force_local"`` => :py:attr:`force_local`

    An example config:

    .. code-block:: python

        {
          "local_resources" :
          {
            "cpus" : 4,
            "mem"  : "2gb"
          },
          "default_local" : True
        }
    """
    super().load_core_config( config, origin )
    resources = config.pop( "local_resources", {} )
    if len( resources ) > 0:
      self.local_resources.add_resources( resources )

    default_local = config.pop( "default_local", None )
    if default_local is not None:
      self.default_local = default_local

    force_local = config.pop( "force_local", None )
    if force_local is not None:
      self.force_local = force_local

  def launch_local( self, requestor : ResourceRequestor ):
    return self.force_local or requestor.local or ( requestor.local is None and self.default_local )

  def resources_available(self, resource_dict : dict, requestor : ResourceRequestor, log=True):
    """Override base class implementation to route local requests to :py:attr:`local_resources`"""
    if self.launch_local( requestor ):
      return self.local_resources.resources_available( resource_dict, requestor, log )
    else:
      return self.nonlocal_resources_available( resource_dict, requestor, log )

  def acquire_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    """Override base class implementation to route local requests to :py:attr:`local_resources`"""
    if self.launch_local( requestor ):
      return self.local_resources.acquire_resources( resource_dict, requestor )
    else:
      return self.nonlocal_acquire_resources( resource_dict, requestor )

  def release_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    """Override base class implementation to route local requests to :py:attr:`local_resources`"""
    if self.launch_local( requestor ):
      return self.local_resources.release_resources( resource_dict, requestor )
    else:
      return self.nonlocal_release_resources( resource_dict, requestor )

  @abstractmethod
  def nonlocal_resources_available( self, resource_dict, requestor : ResourceRequestor, log=True ):
    """Tell us how to determine if nonlocal resources are available"""
    pass

  @abstractmethod
  def nonlocal_acquire_resources( self, resource_dict, requestor : ResourceRequestor ):
    """Tell us how to acquire nonlocal resources"""
    pass

  @abstractmethod
  def nonlocal_release_resources( self, resource_dict, requestor : ResourceRequestor ):
    """Tell us how to release nonlocal resources"""
    pass

  @property
  def resource_log( self ):
    return { "local_resources" : self.local_resources.resource_log }
