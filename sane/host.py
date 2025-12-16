import socket
from typing import Dict

import sane.match as match
import sane.options as opts
import sane.logger as logger
import sane.save_state as state
import sane.utdict as utdict
import sane.environment
import sane.resources
from sane.helpers import copydoc, recursive_update

class Host( match.NameMatch, state.SaveState, sane.resources.ResourceProvider ):
  """Primary :py:class:`~resources.ResourceProvider` and container for :py:class:`Environment` available within a workflow."""
  CONFIG_TYPE = "Host"

  def __init__( self, name, aliases=[] ):
    """Create a host with ``name`` and optional ``aliases``"""
    super().__init__( name=name, aliases=aliases, logname=name, filename=f"host_{name}", base=Host )

    self.environments = utdict.UniqueTypedDict( sane.environment.Environment )
    self.dry_run = False

    self._base_environment = None
    self._resources    = {}
    self._default_env  = None
    self.config          = {}
    #: Control when to kill the :py:attr:`watchdog_func`
    self.kill_watchdog   = False
    self.__wake__        = None

  def match( self, requested_host ):
    return self.partial_match( requested_host )

  def valid_host( self, override_host : str = None ) -> bool:
    """Check if this host should be used for this workflow.
    
    The default check uses the FQDN of current machine as the full string to find
    a partial substring match to this :py:attr:`Host.name`.

    :param override_host: If provided, use this string instead of the FQDN to check
                          for substring matches.
    :return: True if this host is valid for running this workflow on this machine
    """
    requested_host = socket.getfqdn() if override_host is None else override_host
    return self.match( requested_host )

  def has_environment( self, requested_env ) -> sane.environment.Environment:
    """Check if this :py:class:`Host` has the ``requested_env``
    
    If the ``requested_env`` is ``None``, return the :py:attr:`default_env`,
    otherwise try to find the matching :py:class:`Environment` using
    :py:meth:`Environment.match()`.

    :return: the matching :py:class:`Environment` or ``None`` if not found
    """
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
  def default_env( self ) -> sane.environment.Environment:
    """Return the default :py:class:`Environment` or ``None`` if no default is set

    :param: set the default by using the :py:class:`Environment.name`
    """
    if self._default_env is None:
      return None
    else:
      return self.has_environment( self._default_env )

  @default_env.setter
  def default_env( self, env : str ):
    self._default_env = env

  @property
  def base_env( self ):
    """The base :py:class:`Environment` to always setup when running this :py:class:`Host` before
    any specific :py:class:`Environment` requested by :py:class:`Action.environment`

    .. hint:: If a base env is provided, all :py:class:`Environment` in :py:attr:`environments`
              copy specific attributes over using :py:class:`Environment._copy_from_base`

    :param env: A :py:class:`Environment` to use as the base
    """
    return self._base_environment

  @base_env.setter
  def base_env( self, env : sane.environment.Environment ):
    self._base_environment = env
    for env_name, env in self.environments.items():
      env._base = self.base_env

  def add_environment( self, env : sane.environment.Environment ):
    """Add an :py:class:`Environment` to the :py:attr:`environments` using :py:attr:`Environment.name` as the key"""
    env._base = self.base_env
    self.environments[env.name] = env

  @copydoc( opts.OptionLoader.load_core_options, append=False, module="options" )
  @copydoc( sane.resources.ResourceProvider.load_core_options, module="resources" )
  def load_core_options( self, options, origin ):
    """Load the :py:class:`Host` *options* into this instance.
    
    Below is the expected layout, where all fields are optional and ``"<>"`` fields are user-specified:

    .. code-block:: python

        {
          "aliases" : [ ...str.. ],
          "default_env" : "<env-name>",
          "config" : { ...anything... }
          "base_env" : { "type" : "<some_env_type>", ...env options... },
          "environments" :
          {
            "<env-name>" : { "type" : "<some_env_type>", ...env options... },
            ...other env declarations...
          }
        }

    The following keys are loaded to their respective attribute. If not present,
    the attributes are unmodified.

    * ``"aliases"`` => :py:attr:`aliases`
    * ``"default_env"`` => :py:attr:`default_env`

    The following key is loaded and calls :py:func:`~helpers.recursive_update`
    preserve any unmodified existing values:

    * ``"config"`` => :py:attr:`config`

    The ``"base_env"`` key, if present, is processsed to create an :py:class:`Environment`
    that is used to set the :py:attr:`base_env`. Inside of the dict of this key,
    the ``"type"`` field informs which type of :py:class:`Environment` to create.
    If no ``"type"`` is specified, the default is :py:class:`Environment`.

    The ``"environments"`` key is processed by iterating over each ``"<env-name>"`` and its dict.
    Inside of this respective ``"<env-name>"`` dict, the ``"type"`` field informs
    which type of :py:class:`Environment` to create. If no ``"type"`` is specified, the
    default is :py:class:`Environment`.

    For both ``"environments"`` and ``"base_env"``, once the environment instance
    is created, its respective dict is loaded via its own :py:meth:`Environment.load_options`.
    Then the created :py:class:`Environment` is added with :py:meth:`add_environment`

    .. hint::
        See :py:meth:`search_type` for more info on how the ``"type"`` field should be specified.
 
    An example *options* :external:py:class:`dict`:
    
    .. parsed-literal::

        {
          "aliases" : [ "basic", "simple" ]
          # Recall that :py:attr:`config` is a generic ``dict``
          "config"      : { "foo" : [ 1, 2, 3 ], "bar" : "file" },
          "base_env" :
          {
            "type" : "sane.Environment",
            ...env options...
          },
          "environments" :
          {
            "gnu" : { "type" : "sane.Environment", ...env options... }
          }
        }
    """
    aliases = list( set( options.pop( "aliases", [] ) ) )
    if aliases != []:
      self._aliases = aliases

    default_env = options.pop( "default_env", None )
    if default_env is not None:
      self.default_env = default_env

    base_env = options.pop( "base_env", None )
    if base_env is not None:
      if self.base_env is None:
        env_typename = base_env.pop( "type", sane.environment.Environment.CONFIG_TYPE )
        env_type = sane.environment.Environment
        if env_typename != sane.environment.Environment.CONFIG_TYPE:
          env_type = self.search_type( env_typename )

        env = env_type( self.name + "_env" )
      else:
        env = base_env
      env.load_options( base_env, origin )
      self.base_env = env

    env_opts      = options.pop( "environments", {} )
    for id, env_options in env_opts.items():
      if id in self.environments:
        self.log( f"Applying patch to Environment '{id}'" )
        env = self.environments[id]
      else:
        env_typename = env_options.pop( "type", sane.environment.Environment.CONFIG_TYPE )
        env_type = sane.environment.Environment
        # TODO: I think the pickling will fail for custom environments right now without
        # also adding the source defs of the host's envs to its own
        if env_typename != sane.environment.Environment.CONFIG_TYPE:
          env_type = self.search_type( env_typename )

        env = env_type( id )
        self.add_environment( env )

      env.load_options( env_options, origin )

    host_config = options.pop( "config", None )
    if host_config is not None:
      recursive_update( self.config, host_config )

    super().load_core_options( options, origin )

  def pre_launch( self, action : sane.Action ):
    """Called within the main thread just before calling :py:meth:`Action.launch`"""
    pass

  def post_launch( self, action : sane.Action, retval, content ):
    """Called within the main thread afetr completing :py:meth:`Action.launch` with its return values"""
    pass

  def launch_wrapper( self, action : sane.Action, dependencies : Dict[str, sane.Action] ):
    pass

  def pre_run_actions( self, actions : Dict[str, sane.Action] ):
    """Called just before entering the main workflow loop of :py:meth:`Orchestrator.run_actions`

    :param dict[str,Action] actions: The current set of :py:class:`Action` queued in this
                                     workflow, stored by :py:attr:`~Action.id`
    """
    pass

  def post_run_actions( self, actions : Dict[str, sane.Action] ):
    """Called just after exiting the main workflow loop of :py:meth:`Orchestrator.run_actions`

    :param dict[str,Action] actions: The current set of :py:class:`Action` queued in this
                                     workflow, stored by :py:attr:`~Action.id`
    """
    pass

  @property
  def info( self ):
    """:py:class:`Host` info provided as a ``dict`` to the :py:class:`Action`
    at runtime via :py:attr:`Action.host_info`

    The default implementation provides the following:

    .. parsed-literal::
        {
          "file"   : :py:attr:`save_file`,
          "name"   : :py:attr:`name`,
          "config" : :py:attr:`config`,
        }
    """
    info = {}
    info["file"] = self.save_file
    info["name"] = self.name
    info["config"] = self.config
    return info

  def save( self ):
    tmp_wake     = self.__wake__
    tmp_logger   = self.logger
    self.__wake__  = None
    self.logger    = None
    super().save()
    # Now restore
    self.__wake__  = tmp_wake
    self.logger    = tmp_logger

  def __orch_wake__( self ):
    """Wake up the :py:class:`Orchestrator` from another thread.

    This should be used as an event trigger to induce re-evaluation of completed
    :py:class:`Actions <Action>` in the current workflow run.
    See :py:attr:`Orchestrator.__wake__` for more info.
    """
    if self.__wake__ is not None:
      self.__wake__.set()

  @property
  def watchdog_func( self ):
    """Return a callable function that takes one positional argument corresponding to the
    current set of :py:class:`Action` queued in this workflow, stored by :py:attr:`~Action.id`

    The callable returned by this function will be started on a separate thread
    just before :py:meth:`Host.pre_run_actions` is called. It is on the user to
    ensure that this thread can exit when :py:attr:`kill_watchdog` is set to ``True``.

    Default is ``None``

    :return: If ``None`` is returned, no watchdog thread is created.
    """
    return None
