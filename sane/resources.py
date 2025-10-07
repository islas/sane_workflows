from abc import abstractmethod
import re
from datetime import time
import math
import operator
import copy

import sane.logger as logger
import sane.json_config as jconfig
import sane.config as config

# Format using PBS-stye
# http://docs.adaptivecomputing.com/torque/4-1-3/Content/topics/2-jobs/requestingRes.htm
_res_size_regex_str = r"(?P<numeric>-?\d+)(?P<multi>(?P<scale>k|m|g|t)?(?P<unit>b|w)?)"
_res_size_regex     = re.compile( _res_size_regex_str, re.I )
_multipliers    = { "" : 1, "k" : 1024, "m" : 1024**2, "g" : 1024**3, "t" : 1024**4 }

_timelimit_regex_str    = r"^(?P<hh>\d+):(?P<mm>\d+):(?P<ss>\d+)$"
_timelimit_regex        = re.compile( _timelimit_regex_str )
_timelimit_format_str   = "{:02}:{:02}:{:02}"


class Resource:
  def __init__( self, resource, amount=0, unit="" ):
    self._resource = resource
    self._original_amount = None
    self._res_dict = None
    self.amount = amount
    if unit != "":
      self._res_dict["unit"] = unit

  @staticmethod
  def is_resource( potential_resource ):
    res_dict = res_size_dict( potential_resource )
    return res_dict is not None

  @property
  def resource( self ):
    return self._resource

  @property
  def unit( self ):
    return self._res_dict["unit"]

  @property
  def amount( self ):
    return self._original_amount

  @amount.setter
  def amount( self, amount ):
    # Caution, this resets everything
    self._original_amount = amount
    self._res_dict = res_size_expand( res_size_dict( amount ) )
    self._check_bounds()

  @property
  def total( self ):
    return self._res_dict["numeric"]

  @property
  def current( self ):
    return self.total

  @current.setter
  def current( self, amount ):
    self.amount = amount
    self._check_bounds()

  # These are always reduced
  @property
  def total_str( self ):
    return res_size_str( res_size_reduce( self._res_dict ) )

  @property
  def current_str( self ):
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


class AcquirableResource( Resource ):
  def __init__( self, resource, amount ):
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
    return self.acquirable.current

  @current.setter
  def current( self, amount ):
    self.acquirable.current = amount
    self._check_bounds()

  @property
  def used( self ):
    return self.total - self.acquirable.total

  @property
  def used_str( self ):
    res_dict = self._res_dict.copy()
    res_dict["numeric"] = self.used
    return res_size_str( res_size_reduce( res_dict ) )


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

  def add_mapping( self, resource : str, aliases : list[str] ):
    self._mapping[resource] = ResourceMatch( name=resource, aliases=aliases )

  def name( self, resource : str ) -> str:
    for resource_name, resource_match in self._mapping.items():
      if resource_match.match( resource ):
        return resource_name
    return resource


class ResourceRequestor( jconfig.JSONConfig ):
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    self._resources            = {}
    self._override_resources   = {}
    self.local = None

  def resources( self, override : str=None ):
    resource_dict = self._resources.copy()
    if override in self._override_resources:
      jconfig.recursive_update( resource_dict, self._override_resources[override] )
    return resource_dict

  def add_resource_requirements( self, resource_dict : dict ):
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

  def load_core_config( self, config : dict ):
    self.add_resource_requirements( config.pop( "resources", {} ) )

    local = config.pop( "local", None )
    if local is not None:
      self.local = local

    super().load_core_config( config )


class ResourceProvider( jconfig.JSONConfig ):
  def __init__( self, mapper=None, **kwargs ):
    super().__init__( **kwargs )
    self._resources    = {}
    if mapper is None:
      self._mapper = ResourceMapper()
    else:
      self._mapper = mapper

  @property
  def resources( self ):
    return self._resources.copy()

  def add_resources( self, resource_dict : dict, override=False ):
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    for resource, info in mapped_resource_dict.items():
      if not override and resource in self._resources and self._resources[resource].total > 0:
        self.log( f"Resource ''{resource}'' already set, ignoring new resource setting", level=30 )
      else:
        self._resources[resource] = AcquirableResource( resource, info )

  def resources_available( self, resource_dict : dict, requestor : ResourceRequestor, log=True ):
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
      else:
        res = Resource( resource, info, unit=self._resources[resource].unit )
      if resource not in self._resources:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "host does not possess this resource"
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      if res.total > self._resources[resource].total:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "requested amount is greater than available total " + self._resources[resource].total_str
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      acquirable = res.total <= self._resources[resource].current
      if not acquirable and log:
        self.log( f"Resource '{resource}' : {res.total_str} not acquirable right now...", level=10 )
      can_aquire = can_aquire and acquirable

    if log:
      if can_aquire:
        self.log( f"All resources{origin_msg} available", level=10 )
      else:
        self.log( f"Not all resources available", level=10 )
      self.log_pop()
    return can_aquire

  def acquire_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    origin_msg = f" for '{requestor.logname}'"

    self.log( f"Acquiring resources{origin_msg}...", level=10 )
    self.log_push()
    if self.resources_available( mapped_resource_dict, requestor ):
      for resource, info in mapped_resource_dict.items():
        res = None
        if isinstance( info, Resource ):
          res = info
        else:
          res = Resource( resource, info, unit=self._resources[resource].unit )
        self.log( f"Acquiring resource '{resource}' : {res.total_str}", level=10 )
        self._resources[resource] -= res
    else:
      self.log( f"Could not acquire resources{origin_msg}", level=10 )
      self.log_pop()
      return False

    self.log_pop()
    return True

  def release_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    mapped_resource_dict = self.map_resource_dict( resource_dict )
    origin_msg = f" from '{requestor.logname}'"

    self.log( f"Releasing resources{origin_msg}...", level=10 )
    self.log_push()
    for resource, info in mapped_resource_dict.items():
      if resource not in self._resources:
        self.log( f"Cannot return resource '{resource}', instance does not possess this resource", level=30 )

      res = None
      if isinstance( info, Resource ):
        res = info
      else:
        res = Resource( resource, info, unit=self._resources[resource].unit )
      if res.total > self._resources[resource].used:
        msg  = f"Cannot return resource '{resource}' : {res.total_str}, "
        msg += "amount is greater than current in use " + self._resources[resource].used_str
        self.log( msg, level=30 )
      else:
        self.log( f"Releasing resource '{resource}' : {res.total_str}", level=10 )
        self._resources[resource] += res
    self.log_pop()

  def load_core_config( self, config ):
    resources = config.pop( "resources", {} )
    if len( resources ) > 0:
      self.add_resources( resources )

    mapping = config.pop( "mapping", {} )
    for resource, aliases in mapping.items():
      self._mapper.add_mapping( resource, aliases )

    super().load_core_config( config )

  def map_resource( self, resource : str ):
    """Map everything to internal name"""
    mapped_resource = self._mapper.name( resource )
    res_split = resource.split( ":" )
    if len( res_split ) == 2:
      mapped_resource = "{0}:{1}".format( self._mapper.name( res_split[0] ), res_split[1] )
    return mapped_resource

  def map_resource_dict( self, resource_dict : dict, log=False ):
    """Map entire dict to internal names"""
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


class NonLocalProvider( ResourceProvider ):
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    self.default_local = False
    self.force_local = False
    self.local_resources = ResourceProvider( mapper=self._mapper, logname=f"{self.logname}::local" )

  def load_core_config( self, config ):
    resources = config.pop( "local_resources", {} )
    if len( resources ) > 0:
      self.local_resources.add_resources( resources )

    default_local = config.pop( "default_local", None )
    if default_local is not None:
      self.default_local = default_local

    force_local = config.pop( "force_local", None )
    if force_local is not None:
      self.force_local = force_local

    super().load_core_config( config )

  def launch_local( self, requestor : ResourceRequestor ):
    return self.force_local or requestor.local or ( requestor.local is None and self.default_local )

  def resources_available(self, resource_dict : dict, requestor : ResourceRequestor, log=True):
    if self.launch_local( requestor ):
      return self.local_resources.resources_available( resource_dict, requestor, log )
    else:
      return self.nonlocal_resources_available( resource_dict, requestor, log )

  def acquire_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
    if self.launch_local( requestor ):
      return self.local_resources.acquire_resources( resource_dict, requestor )
    else:
      return self.nonlocal_acquire_resources( resource_dict, requestor )

  def release_resources( self, resource_dict : dict, requestor : ResourceRequestor ):
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
