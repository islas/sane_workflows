import socket

import sane.config as config
import sane.environment
import sane.json_config as jconfig
import sane.logger as logger
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

  def load_core_config( self, **kwargs ):
    aliases = list( set( kwargs.pop( "aliases", [] ) ) )
    if aliases != [] : self._aliases = aliases

    default_env = kwargs.pop( "default_env", None )
    if default_env is not None : self.default_env = default_env

    lmod_path = kwargs.pop( "lmod_path", None )
    if lmod_path is not None : self.lmod_path = lmod_path

    env_configs      = kwargs.pop( "environments", {} )
    for id, env_config in env_configs.items():
      env_typename = env_config.pop( "type", sane.environment.Environment.CONFIG_TYPE )
      env_type = sane.environment.Environment
      if env_typename == sane.environment.Environment.CONFIG_TYPE:
        env_type = self.search_type( env_typename )

      env = env_type( id )
      env.load_config( env_config )

      self.add_environment( env )
