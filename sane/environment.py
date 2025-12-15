import importlib
import sys
import os
import contextlib
import io
from collections import OrderedDict
from subprocess import PIPE, Popen


import sane.match as match
import sane.options as opts
from sane.helpers import copydoc

def env_from_script( script, *arguments, **kwargs ):
  """
  Execute a script, compare environment changes and then apply to
  the current Python environment (i.e. `os.environ`_).

  Raises an exception in case script execution returned a non-zero
  exit code.

  Use with keyword argument show_environ_updates=True to show the actual
  changes made to `os.environ`_ (mostly for debugging).

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
  print( stderr.decode(), file=err_out )

  if ( 'show_environ_updates' in kwargs ):
    print( stdout.decode() )
  if status == 0:
    exec( stdout.decode() )
  else:
    print( stdout.decode() )
    raise RuntimeError( "Failed to run env_from_script" )
  return status, stderr.decode()


class Environment( match.NameMatch, opts.OptionLoader ):
  """Control the setup of an environment on a particular :py:class:`Host`"""
  LMOD_MODULE = "env_modules_python"
  CONFIG_TYPE = "Environment"

  def __init__( self, name, aliases=[], lmod_path=None ):
    """Create a host with ``name`` and optional ``aliases`` and ``lmod_path``
    
    If a :py:class:`Host` has a :py:attr:`Host.base_env`, by default the
    ``lmod_path`` of that base env will be copied over during :py:meth:`setup()`
    """
    super().__init__( name=name, logname=name, aliases=aliases )
    # This should only be set by the parent host
    self._base = None

    #: Path to lmod python module containing the ``module()`` function call
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
    """Execute lmod commands in a :external:py:class:`subprocess.Popen` and return
    the python commands to emulate the environment changes.
    """
    self.find_lmod()
    output = io.StringIO()
    with contextlib.redirect_stdout( output ) as fs:
      with contextlib.redirect_stderr( output ) as fe:
        self._lmod.module( cmd, *args, **kwargs )
    for line in output.getvalue().splitlines():
      self.log( line, level=25 )

  def env_var_prepend( self, var, val ):
    """Prepend ``val`` to environment variable ``var``"""
    os.environ[var] = "{0}:{1}".format( val, os.environ[var] )

  def env_var_append( self, var, val ):
    """Append ``val`` to environment variable ``var``"""
    os.environ[var] = "{1}:{0}".format( val, os.environ[var] )

  def env_var_set( self, var, val ):
    """Set environment variable ``var`` to ``val``"""
    os.environ[var] = str( val )

  def env_var_unset( self, var ):
    """Unset environment variable ``var``"""
    os.environ.pop( var, None )

  def env_script( self, script ):
    """Execute a script in a :external:py:class:`subprocess.Popen` and return
    the python commands to emulate the environment changes.
    """
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

  def setup_lmod_cmds( self, cmd : str, *args : str, category="unassigned", **kwargs ):
    """Store lmod commands to execute later during :py:meth:`setup()`

    These commands will eventually be executed within the isolated subprocess of
    :py:meth:`Action.run()`. The ``cmd`` should be the first argument one would
    use for `module`_ command. All arguments that follow are appended to execution.
    ``**kwargs`` is reseved for the python ``module()`` function implementation.

    Example usage for recreating ``module purge && module load gcc/12.4.0``:

    .. code-block:: python

        self.setup_lmod_cmds( "purge" )
        self.setup_lmod_cmds( "load", "gcc/12.4.0" )

    If a ``category`` is passed in, commands are grouped based on the ``category``
    and during evaluation are executed in order of ``category`` creation then
    command insertion order (first ``category`` and first command input go first).

    :param cmd:  first argument to command line ``module`` command
    :param args: all other arguments to command line ``module`` command
    :param category: category to group this command under
    """
    if category not in self._setup_lmod_cmds:
      self._setup_lmod_cmds[category] = []

    self._setup_lmod_cmds[category].append( ( cmd, args, kwargs ) )

  def setup_env_vars( self, cmd : str, var : str, val=None, category="unassigned" ):
    """Store environment variable commands to execute later during :py:meth:`setup()`

    These commands will eventually be executed within the isolated subprocess of
    :py:meth:`Action.run()`. The ``cmd`` should be one of { ``"set"``, ``"unset"``,
    ``"prepend"``, ``"append"`` }. The ``val`` is used for all eventual calls except
    ``"unset"``. The ``cmd`` corresponds to a respective call used in :py:meth:`setup()`

    Example usage for recreating ``export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/new/path/``:

    .. code-block:: python

        self.setup_env_vars( "append", "LD_LIBRARY_PATH", "/new/path/" )

    .. warning:: `os.environ`_ uses values verbatim and does not expand values.
                 ``setup_env_vars( "append", "LD_LIBRARY_PATH", "$NEW_PATH" )``
                 with ``NEW_PATH=/new/path`` would not produce the intended effect.
                 Currently, the ``env_var_*`` methods do not expand values automatically.

    If a ``category`` is passed in, commands are grouped based on the ``category``
    and during evaluation are executed in order of ``category`` creation then
    command insertion order (first ``category`` and first command input go first).

    :param cmd: one of { ``"set"``, ``"unset"``, ``"prepend"``, ``"append"`` }
    :param var: environment variable to modify
    :param val: value to use during modification, if applicable
    :param category: category to group this command under
    """
    # This should be switched to an enum.. probably...
    cmds = [ "set", "unset", "prepend", "append" ]
    if cmd not in cmds:
      raise Exception( f"Environment variable cmd must be one of {cmds}")

    if category not in self._setup_env_vars:
      self._setup_env_vars[category] = []

    self._setup_env_vars[category].append( ( cmd, var, val ) )

  def setup_scripts( self, *scripts : str ):
    """Store scripts execute later during :py:meth:`setup()`

    These scripts should modify the execution environment silently. Internally,
    to capture the effects from a subprocess, the difference in `env`_ output
    after running the script and output python commands to emulate this effect.

    .. danger:: The script **MUST** be silent in output.

    :param scripts: Any number of script paths to execute during :py:meth:`setup()`
    """
    self._setup_scripts.extend( list( scripts ) )

  def _copy_from_base( self ):
    """Copy values from the :py:attr:`Host.base_env` to this instance

    By default only the lmod information is copied over so that this
    instance does not need to reload the lmod python module.
    """
    self.lmod_path = self._base.lmod_path
    self._lmod     = self._base._lmod

  def pre_setup( self ):
    """Called just before :py:meth:`setup()`"""
    pass

  def post_setup( self ):
    """Called just after :py:meth:`setup()`"""
    pass

  def setup( self ):
    """Setup the environment
    
    If a base env is present, call the :py:meth:`setup()` for that :py:class:`Environment`
    first. Then call :py:meth:`_copy_from_base` to ensure this instance has the
    relevant information.

    Setup of this :py:class:`Environment` follows this order:

    1. Scripts stored from :py:meth:`setup_scripts` are executed via :py:meth:`env_script`
    2. lmod commands stored from :py:meth:`setup_lmod_cmds` are executed via :py:meth:`module`
    3. env commands stored from :py:meth:`setup_env_vars` are executed using the respective
       command call:

      * ``"set"`` => :py:meth:`env_var_set`
      * ``"unset"`` => :py:meth:`env_var_unset`
      * ``"prepend"`` => :py:meth:`env_var_prepend`
      * ``"append"`` => :py:meth:`env_var_append`

    Setup commands with ``category`` are executed in order of ``category`` creation then
    command insertion order (first ``category`` and first command input go first).
    """
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
    """Return true if :py:attr:`~Environment.name` or :py:attr:`~Environment.aliases` is an exact match to ``requested_env``"""
    return self.exact_match( requested_env )

  @copydoc( opts.OptionLoader.load_core_options, append=False )
  def load_core_options( self, options, origin ):
    """Load the *options* into this :py:class:`Environment`
    
    The following keys are loaded to their respective attribute. If not present,
    the attributes are unmodified.

    * ``"aliases"`` => :py:attr:`aliases`
    * ``"lmod_path"`` => :py:attr:`lmod_path`

    The following key is iterated over, where each dict is then expanded
    to keyword arguments directly calling :py:meth:`setup_env_vars`

    * ``"env_vars"``

    The following key is iterated over, where for each dict ``"cmd"`` and ``"args"``
    are extracted as positional arguments and the remainder is expanded to keyword
    arguments directly calling :py:meth:`setup_lmod_cmds`

    * ``"lmod_cmds"``

    The following key is loaded verbatim using :py:meth:`setup_scripts`:

    * ``"env_scripts"``

    An example *options* :external:py:class:`dict`:

    .. code-block:: python

        {
          "aliases" : [ "generic", "maybe something else" ],
          "lmod_path" : "<path to lmod>",
          "env_vars"  :
          [
            { "cmd" : "prepend", "var" : "foo", "val" : 0 },
            { "cmd" : "append", "var" : "bar", "val" : "/path/" }
          ],
          "lmod_cmds" :
          [
            { "cmd" : "load", "args" : [ "gcc", "netcdf" ] }
          ]
          "env_scripts" :
          [
            "/etc/profile.d/z00_modules.sh",
            "/some/other/profile/script.sh"
          ]
        }
    """
    aliases = list( set( options.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    self.setup_scripts( *options.pop( "env_scripts", [] ) )

    lmod_path = options.pop( "lmod_path", None )
    if lmod_path is not None:
      self.lmod_path = lmod_path

    for env_cmd in options.pop( "env_vars", [] ):
      self.setup_env_vars( **env_cmd )

    for lmod_cmd in options.pop( "lmod_cmds", [] ):
      cmd  = lmod_cmd.pop( "cmd" )
      args = lmod_cmd.pop( "args", [] )
      self.setup_lmod_cmds( cmd, *args, **lmod_cmd )
    super().load_core_options( options, origin )
