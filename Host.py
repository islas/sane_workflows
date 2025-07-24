from abc import ABCMeta, abstractmethod
import socket

from Config import Config
from Environment import Environment
import UniqueTypedDict as utd

class Host( Config ):
  def __init__( self, name, aliases=[] ):
    super().__init__( name, aliases )

    self.environments  = utd.UniqueTypedDict( Environment )
    self.resources_    = {}

    self.default_env_  = None

  def match( self, requested_host ):
    return self.partial_match( requested_host )

  def valid_host( self, override_host=None ):
    requested_host = socket.getfqdn() if override_host is None else override_host
    return self.match( requested_host )

  def has_environment( self, requested_env ):
    found  = False
    env_id = None
    for env_name, environment in self.environments.items():
      found = environment.match( requested_env )
      if found:
        env_id = env_name
        break
    
    return found, env_id
  
  def default_env( self ):
    if self.default_env_ is None:
      return False, None
    
    else:
      return self.has_environment( self.default_env_ )
  
  def add_environment( self, env ):
    self.environments[env.name_] = env
