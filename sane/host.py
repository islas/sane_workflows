import socket

import sane.config as config
import sane.environment
import sane.json_config as jconfig
import sane.logger as logger
import sane.resource_helpers as reshelpers
import sane.save_state as state
import sane.utdict as utdict


class Host( config.Config, state.SaveState, jconfig.JSONConfig ):
  CONFIG_TYPE = "Host"

  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases, filename=f"host_{name}", base=Host )

    self.environments  = utdict.UniqueTypedDict( sane.environment.Environment )
    self.lmod_path     = None
    self._resources    = {}

    self._default_env  = None

  def match( self, requested_host ):
    return self.partial_match( requested_host )

  def valid_host( self, override_host=None ):
    requested_host = socket.getfqdn() if override_host is None else override_host
    return self.match( requested_host )

  def has_environment( self, requested_env ):
    if requested_env is None:
      # Note that this is the property
      return self.default_env

    env = None
    for env_name, environment in self.environments.items():
      found = environment.match( requested_env )
      if found:
        env = environment
        break

    return env

  @property
  def default_env( self ):
    if self._default_env is None:
      return None
    else:
      return self.has_environment( self._default_env )

  @default_env.setter
  def default_env( self, env ):
    self._default_env = env

  def add_environment( self, env ):
    if env.lmod_path is None and self.lmod_path is not None:
      env.lmod_path = self.lmod_path
    self.environments[env.name] = env

  def load_core_config( self, config ):
    aliases = list( set( config.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    default_env = config.pop( "default_env", None )
    if default_env is not None:
      self.default_env = default_env

    lmod_path = config.pop( "lmod_path", None )
    if lmod_path is not None:
      self.lmod_path = lmod_path

    self.add_resources( config.pop( "resources", {} ) )

    env_configs      = config.pop( "environments", {} )
    for id, env_config in env_configs.items():
      env_typename = env_config.pop( "type", sane.environment.Environment.CONFIG_TYPE )
      env_type = sane.environment.Environment
      if env_typename == sane.environment.Environment.CONFIG_TYPE:
        env_type = self.search_type( env_typename )

      env = env_type( id )
      env.load_config( env_config )

      self.add_environment( env )

  def add_resources( self, resource_dict ):
    for resource, info in resource_dict.items():
      if resource in self._resources:
        self.log( f"Resource ''{resource}'' already set, ignoring new resource setting", level=30 )
      else:
        self._resources[resource] = reshelpers.res_size_expand( reshelpers.res_size_dict( str(info) ) )
        self._resources[resource]["in_use"] = 0.0

  def resources_available( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" for {requestor}"

    self.log( f"Checking if resources available{origin_msg}..." )
    self.log_push()
    can_aquire = True
    for resource, info in resource_dict.items():
      res_size_dict = reshelpers.res_size_dict( info )
      if resource not in self._resources:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "host does not possess this resource"
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      req_amount = reshelpers.res_size_base( res_size_dict )
      if req_amount > self._resources[resource]["numeric"]:
        msg  = f"Will never be able to acquire resource '{resource}' : {info}, "
        msg += "requested amount is greater than available total " + reshelpers.res_size_str(self._resources[resource])
        self.log( msg, level=50 )
        self.log_pop()
        raise Exception( msg )

      acquirable = ( req_amount + self._resources[resource]["in_use"] ) <= self._resources[resource]["numeric"]
      if not acquirable:
        self.log( f"Resource '{resource}' : {amount}{base_unit} not acquirable right now..." )
      can_aquire = can_aquire and acquirable
    self.log( f"All resources{origin_msg} available" )
    self.log_pop()
    return can_aquire

  def acquire_resource( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" for {requestor}"

    self.log( f"Acquiring resources{origin_msg}..." )
    self.log_push()
    if self.resources_available( resource_dict, requestor ):
      for resource, info in resource_dict.items():
        self.log( f"Acquiring resource '{resource}' : {info}")
        self._resources[resource]["in_use"] += reshelpers.res_size_base( reshelpers.res_size_dict( info ) )
    else:
      self.log( f"Could not acquire resources{origin_msg}", level=30 )
      self.log_pop()
      return False

    self.log_pop()
    return True

  def release_resources( self, resource_dict, requestor=None ):
    origin_msg = ""
    if requestor is not None:
      origin_msg = f" from {requestor}"

    self.log( f"Releasing resources{origin_msg}..." )
    self.log_push()
    for resource, info in resource_dict.items():
      if resource not in self._resources:
        self.log( f"Cannot return resource '{resource}', instance does not possess this resource", level=30 )
      amount = reshelpers.res_size_base( reshelpers.res_size_dict( info ) )
      in_use = self._resources[resource]["in_use"]
      if ( in_use - amount ) < 0:
        tmp = self._resources[resource].copy()
        tmp["numeric"] = in_use
        msg  = f"Cannot return resource '{resource}' : {info}, "
        msg += "amount is greater than current in use " + reshelpers.res_size_str( tmp )
        self.log( msg, level=30 )
      else:
        self.log( f"Releasing resource '{resource}' : {info}" )
        self._resources[resource]["in_use"] -= amount
    self.log_pop()
