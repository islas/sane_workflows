import importlib
import sys
import os
from collections import OrderedDict

import sane.config as config
import sane.json_config as jconfig


class Environment( config.Config, jconfig.JSONConfig ):
  LMOD_MODULE = "env_modules_python"
  CONFIG_TYPE = "Environment"

  def __init__( self, name, aliases=[], lmod_path=None ):
    super().__init__( name, aliases )

    self.lmod_path  = lmod_path
    self._lmod     = None

    self._setup_env_vars  = OrderedDict()
    self._setup_lmod_cmds = OrderedDict()

  def find_lmod( self, required=True ):
    if self._lmod is None and self.lmod_path is not None:
      if self.lmod_path not in sys.path:
        sys.path.append( self.lmod_path )

      # Find if module available
      spec = importlib.util.find_spec( Environment.LMOD_MODULE )
      if spec is not None:
        self._lmod = importlib.util.module_from_spec( spec )
        spec.loader.exec_module( self._lmod )

    if required and self._lmod is None:
      raise ModuleNotFoundError( f"No module named {Environment.LMOD_MODULE}", name=Environment.LMOD_MODULE )

    return self._lmod is not None

  # Just a simple wrappers to facilitate deferred environment setting
  def module( self, cmd, *args, **kwargs ):
    self.find_lmod()
    self._lmod.module( cmd, *args, **kwargs )

  def env_var_prepend( self, var, val ):
    os.environ[var] = "{0}:{1}".format( val, os.environ[var] )

  def env_var_append( self, var, val ):
    os.environ[var] = "{1}:{0}".format( val, os.environ[var] )

  def env_var_set( self, var, val ):
    os.environ[var] = val

  def env_var_unset( self, var ):
    os.environ.pop( var, None )

  def reset_env_setup( self ):
    self._setup_lmod_cmds.clear()
    self._setup_env_vars.clear()

  def setup_lmod_cmds( self, cmd, *args, category="unassigned", **kwargs ):
    if category not in self._setup_lmod_cmds:
      self._setup_lmod_cmds[category] = []

    self._setup_lmod_cmds[category].append( ( cmd, args, kwargs ) )

  def setup_env_vars( self, cmd, var, val=None, category="unassigned" ):
    # This should be switched to an enum.. probably...
    cmds = [ "set", "unset", "prepend", "append" ]
    if cmd not in cmds:
      raise Exception( f"Environment variable cmd must be one of {cmds}")

    if category not in self._setup_env_vars:
      self._setup_env_vars[category] = []

    self._setup_env_vars[category].append( ( cmd, var, val ) )

  def pre_setup( self ):
    pass

  def post_setup( self ):
    pass

  def setup( self ):
    self.pre_setup()

    # LMOD first to ensure any mass environment changes are seen before user-specific
    # environment manipulation
    for category, lmod_cmd in self._setup_lmod_cmds.items():
      for cmd, args, kwargs in lmod_cmd:
        self.module( cmd, *args, **kwargs )

    for category, env_cmd in self._setup_env_vars.items():
      for cmd, var, val in env_cmd:
        if cmd == "set":
          self.env_var_set( var, val )
        elif cmd == "unset":
          self.env_var_unset( var, val )
        elif cmd == "append":
          self.env_var_append( var, val )
        elif cmd == "prepend":
          self.env_var_prepend( var, val )

    self.post_setup()

  def match( self, requested_env ):
    return self.exact_match( requested_env )

  def load_core_config( self, config ):
    aliases = list( set( config.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    lmod_path = config.pop( "lmod_path", None )
    if lmod_path is not None:
      self.lmod_path = lmod_path

    for env_cmd in config.pop( "env_vars", [] ):
      self.setup_env_vars( **env_cmd )

    for lmod_cmd in config.pop( "lmod_cmds", [] ):
      cmd  = lmod_cmd.pop( "cmd" )
      args = lmod_cmd.pop( "args", None )
      self.setup_lmod_cmds( cmd, *args, **lmod_cmd )
