import importlib
import sys
import os
from collections import OrderedDict

from Config import Config

class Environment( Config ):
  LMOD_MODULE = "env_modules_python"

  def __init__( self, name, aliases=[], lmod_pgk=None ):
    super().__init__( name, aliases )
    
    self.lmod_pgk_ = lmod_pgk
    self.lmod_     = None

    self.setup_env_vars_  = OrderedDict()
    self.setup_lmod_cmds_ = OrderedDict()

  
  def find_lmod( self, required=True ):
    if self.lmod_ is None and self.lmod_pgk_ is not None:
      if self.lmod_pgk_ not in sys.path:
        sys.path.append( lmod_pgk )
      
      # Find if module available
      spec = importlib.util.find_spec( Environment.LMOD_MODULE )
      if spec is not None:
        self.lmod_ = importlib.util.module_from_spec( spec )

    if required and self.lmod_ is None:
      raise ModuleNotFoundError( f"No module named {Environment.LMOD_MODULE}", name=Environment.LMOD_MODULE )

    return self.lmod_ is not None    

  # Just a simple wrappers to facilitate deferred environment setting
  def module( self, cmd, *args, **kwargs ):
    self.find_lmod()
    self.lmod_.module( cmd, *args, **kwargs )
  
  def env_var_prepend( self, var, val ):
    os.environ[var] = "{0}:{1}".format( val, os.environ[var] )
  
  def env_var_append( self, var, val ):
    os.environ[var] = "{1}:{0}".format( val, os.environ[var] )
  
  def env_var_set( self, var, val ):
    os.environ[var] = val
  
  def env_var_unset( self, var ):
    os.environ.pop( var, None )
  
  def reset_env_setup( self ):
    self.setup_lmod_cmds_.clear()
    self.setup_env_vars_.clear()

  def setup_lmod_cmds( self, cmd, *args, category="unassigned", **kwargs ):
    if category not in self.setup_lmod_cmds_:
      self.setup_lmod_cmds_[category] = []

    self.setup_lmod_cmds_[category].append( ( cmd, args, kwargs ) )
  
  def setup_env_vars( self, cmd, var, val=None, category="unassigned" ):
    # This should be switched to an enum.. probably...
    cmds = [ "set", "unset", "prepend", "append" ]
    if cmd not in cmds:
      raise Exception( f"Environment variable cmd must be one of {cmds}")
    
    if category not in self.setup_env_vars_:
      self.setup_env_vars_[category] = []
      
    self.setup_env_vars_[category].append( ( cmd, var, val ) )
  
  def pre_setup( self ):
    pass
  
  def post_setup( self ):
    pass

  def setup( self ):
    # LMOD first to ensure any mass environment changes are seen before user-specific
    # environment manipulation
    for category, lmod_cmd in self.setup_lmod_cmds_.items():
      for cmd, args, kwargs in lmod_cmd:
        self.module( cmd, *args, **kwargs )
    
    for category, env_cmd in self.setup_env_vars_.items():
      for cmd, var, val in env_cmd:
        if cmd == "set":
          self.env_var_set( var, val )
        elif cmd == "unset":
          self.env_var_unset( var, val )
        elif cmd == "append":
          self.env_var_append( var, val )
        elif cmd == "prepend":
          self.env_var_prepend( var, val )

  def match( self, requested_env ):
    return self.exact_match( requested_env )
