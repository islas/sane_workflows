import socket

import sane.config as config
import sane.utdict as utdict
import sane.environment as environment
import sane.save_state as state


class Host( config.Config, state.SaveState ):
  def __init__( self, name, aliases=[] ):
    super().__init__( name=name, aliases=aliases, filename=f"host_{name}.pkl" )

    self.environments  = utdict.UniqueTypedDict( environment.Environment )
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
    self.environments[env.name] = env
