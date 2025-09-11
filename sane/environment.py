import importlib
import sys
import os
import contextlib
import io
from collections import OrderedDict
from subprocess import PIPE, Popen


import sane.config as config
import sane.json_config as jconfig



def env_from_script( script, *arguments, **kwargs ):
  """
  Execute a script, compare environment changes and then apply to
  the current Python environment (i.e. os.environ).

  Raises an exception in case script execution returned a non-zero
  exit code.

  Use with keyword argument show_environ_updates=True to show the actual
  changes made to os.environ (mostly for debugging).

  Modeled after lmod env_modules_python
  """
  numArgs = len(arguments)
  A = [ os.path.abspath( os.path.join( os.path.dirname( __file__ ), "./env_from_script.sh" ) ), script ]
  if (numArgs == 1):
    A += arguments[0].split()
  else:
    A += list(arguments)

  proc           = Popen(A, stdout=PIPE, stderr=PIPE)
  stdout, stderr = proc.communicate()
  status         = proc.returncode
  err_out        = sys.stderr
  print(stderr.decode(),file=err_out)

  if ('show_environ_updates' in kwargs):
    print(stdout.decode())
  if status == 0:
    exec(stdout.decode())
  else:
    print( stdout.decode() )
    raise RuntimeError( "Failed to run env_from_script" )
  return status, stderr.decode()


class Environment( config.Config, jconfig.JSONConfig ):
  LMOD_MODULE = "env_modules_python"
  CONFIG_TYPE = "Environment"

  def __init__( self, name, aliases=[], lmod_path=None ):
    super().__init__( name=name, logname=name, aliases=aliases )
    # This should only be set by the parent host
    self._base = None

    self.lmod_path  = lmod_path
    self._lmod     = None

    self._setup_env_vars  = OrderedDict()
    self._setup_lmod_cmds = OrderedDict()
    self._setup_scripts   = []

  def find_lmod( self, required=True ):
    if self._lmod is None and self.lmod_path is not None:
      # Find if module available
      spec = importlib.util.find_spec( Environment.LMOD_MODULE )
      if spec is None:
        # Try to load it manually
        spec = importlib.util.spec_from_file_location( Environment.LMOD_MODULE, self.lmod_path )

      if spec is not None:
        self._lmod = importlib.util.module_from_spec( spec )
        sys.modules[Environment.LMOD_MODULE] = self._lmod
        spec.loader.exec_module( self._lmod )

    if required and self._lmod is None:
      raise ModuleNotFoundError( f"No module named {Environment.LMOD_MODULE}", name=Environment.LMOD_MODULE )

    return self._lmod is not None

  # Just a simple wrappers to facilitate deferred environment setting
  def module( self, cmd, *args, **kwargs ):
    self.find_lmod()
    output = io.StringIO()
    with contextlib.redirect_stdout( output ) as fs:
      with contextlib.redirect_stderr( output ) as fe:
        self._lmod.module( cmd, *args, **kwargs )
    for line in output.getvalue().splitlines():
      self.log( line, level=25 )

  def env_var_prepend( self, var, val ):
    os.environ[var] = "{0}:{1}".format( val, os.environ[var] )

  def env_var_append( self, var, val ):
    os.environ[var] = "{1}:{0}".format( val, os.environ[var] )

  def env_var_set( self, var, val ):
    os.environ[var] = str( val )

  def env_var_unset( self, var ):
    os.environ.pop( var, None )

  def env_script( self, script ):
    output = io.StringIO()
    with contextlib.redirect_stdout( output ) as fs:
      with contextlib.redirect_stderr( output ) as fe:
        env_from_script( script )
    for line in output.getvalue().splitlines():
      self.log( line, level=25 )

  def reset_env_setup( self ):
    self._setup_lmod_cmds.clear()
    self._setup_env_vars.clear()
    self._setup_scripts.clear()

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

  def setup_scripts( self, script ):
    self._setup_scripts.append( script )

  def _copy_from_base( self ):
    self.lmod_path = self._base.lmod_path
    self._lmod     = self._base._lmod

  def pre_setup( self ):
    pass

  def post_setup( self ):
    pass

  def setup( self ):
    self.pre_setup()

    # Use base to get initially up and running
    if self._base is not None:
      self.log( f"Setting up base '{self._base.name}'" )
      self._base.setup()
      self._copy_from_base()

    # Scripts FIRST
    for script in self._setup_scripts:
      self.log( f"Running script {script}" )
      self.env_script( script )

    # LMOD next to ensure any mass environment changes are seen before user-specific
    # environment manipulation
    for category, lmod_cmd in self._setup_lmod_cmds.items():
      for cmd, args, kwargs in lmod_cmd:
        self.log( f"Running lmod cmd: '{cmd}' with args: '{args}' and kwargs: '{kwargs}'" )
        self.module( cmd, *args, **kwargs )

    for category, env_cmd in self._setup_env_vars.items():
      for cmd, var, val in env_cmd:
        self.log( f"Running env cmd: '{cmd}' with var: '{var}' and val: '{val}'" )
        if cmd == "set":
          self.env_var_set( var, val )
        elif cmd == "unset":
          self.env_var_unset( var, val )
        elif cmd == "append":
          self.env_var_append( var, val )
        elif cmd == "prepend":
          self.env_var_prepend( var, val )
        self.log( f"  Environment variable {var}=" + os.environ[var] )

    self.post_setup()

  def match( self, requested_env ):
    return self.exact_match( requested_env )

  def load_core_config( self, config ):
    aliases = list( set( config.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    for script in config.pop( "env_scripts", [] ):
      self.setup_scripts( script )

    lmod_path = config.pop( "lmod_path", None )
    if lmod_path is not None:
      self.lmod_path = lmod_path

    for env_cmd in config.pop( "env_vars", [] ):
      self.setup_env_vars( **env_cmd )

    for lmod_cmd in config.pop( "lmod_cmds", [] ):
      cmd  = lmod_cmd.pop( "cmd" )
      args = lmod_cmd.pop( "args", None )
      self.setup_lmod_cmds( cmd, *args, **lmod_cmd )
