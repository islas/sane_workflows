import os
import shutil
import re
import io
import subprocess
import threading
import datetime
import time
from typing import Dict, List, Tuple, Union
from enum import Enum, EnumMeta

import sane.logger as slogger
import sane.save_state as state
import sane.json_config as jconfig
import sane.action_launcher as action_launcher
import sane.resources as res
from sane.helpers import copydoc


class ValueMeta( EnumMeta ):
  def __contains__( cls, item ):
    try:
      cls( item )
    except ValueError:
      return False
    return True


class DependencyType( str, Enum, metaclass=ValueMeta ):
  """Types of dependencies between actions from child to parent"""
  AFTEROK    = "afterok"     #: after successful run (this is the default)
  AFTERNOTOK = "afternotok"  #: after failure
  AFTERANY   = "afterany"    #: after either failure or success
  AFTER      = "after"       #: after the step *starts*

  def __str__( self ):
    return str( self.value )

  def __repr__( self ):
    return str( self.value )


class ActionState( Enum ):
  """States that an action may be in"""
  PENDING  = "pending"    #: queued for running
  RUNNING  = "running"    #: currently executing
  FINISHED = "finished"   #: completed regardless of success
  INACTIVE = "inactive"   #: never queued or run, idle
  SKIPPED  = "skipped"    #: never run due to dependencies missing
  ERROR    = "error"      #: reserved for internal use, use action status for action failure


  @classmethod
  def valid_run_state( cls, state ):
    return state == cls.PENDING or state == cls.RUNNING


class ActionStatus( Enum ):
  """Final status of an action

  .. note:: Note that the ``SUBMITTED`` status is considered "completed" in the
            context of action queueing, but final ``SUCCESS`` or ``FAILURE``
            is left to the host implementation.
  """
  SUCCESS   = "success"    #: completed successfully
  FAILURE   = "failure"    #: completed unsuccessfully
  SUBMITTED = "submitted"  #: submitted to host, current context action completed but execution left to host
  NONE      = "none"       #: no completion status to report


class RequirementsState( Enum ):
  MET     = "met"
  PENDING = "pending"
  UNMET   = "unmet"

  @classmethod
  def reduce_state( cls, *args ):
    state = cls.MET
    for arg in args:
      if ( isinstance( arg, bool ) and arg == True ) or arg == cls.MET:
        continue
      if arg == cls.PENDING:
        state = cls.PENDING
      elif ( isinstance( arg, bool ) and arg == False ) or arg == cls.UNMET:
        state = cls.UNMET
        break
    return state


def _dependency_met( dep_type, state, status, submit_ok ):
  if dep_type != DependencyType.AFTER:
    if state == ActionState.FINISHED:
      if dep_type == DependencyType.AFTERANY:
        return RequirementsState.MET
      else:
        # Writing out the checks explicitly, submitted is an ambiguous state and
        # so can count for both... maybe this should be reconsidered later
        if dep_type == DependencyType.AFTEROK:
          if status == ActionStatus.SUCCESS:
            return RequirementsState.MET
          elif status == ActionStatus.SUBMITTED:
            return RequirementsState.MET if submit_ok else RequirementsState.PENDING
        elif dep_type == DependencyType.AFTERNOTOK:
          if status == ActionStatus.FAILURE:
            return RequirementsState.MET
          elif  status == ActionStatus.SUBMITTED:
            return RequirementsState.MET if submit_ok else RequirementsState.PENDING
  elif dep_type == DependencyType.AFTER:
    if state == ActionState.RUNNING or state == ActionState.FINISHED:
      return RequirementsState.MET
    elif status == ActionStatus.SUBMITTED:
      # It would require the submit host to tell us when this is running
      return RequirementsState.MET if submit_ok else RequirementsState.PENDING
  # Everything else
  return RequirementsState.UNMET


class Action( state.SaveState, res.ResourceRequestor ):
  """A single task

  An Action is the singular unit within workflows that performs work. Actions
  will always be in one of a finite set of states with an associated status.

  * Actions can specify an :py:attr:`Environment <sane.Environment.name>` necessary to run
  * Actions can specify resources necessry to run
  * Actions can specify :py:class:`dependencies <sane.DependencyType>` necessry to run
  * Actions must have unique IDs within a workflow
  * Actions will always execute under separate processes from the :py:class:`sane.Orchestrator`
  """
  CONFIG_TYPE = "Action"
  REF_RE = re.compile( r"(?P<substr>[$]{{[ ]*(?P<attrs>(?:\w+(?:\[\d+\])?\.)*\w+(?:\[\d+\])?)[ ]*}})" )
  IDX_RE = re.compile( r"(?P<attr>\w+)(?:\[(?P<idx>\d+)\])?" )

  def __init__( self, id ):
    """Create an Action with unique ID"""
    self._id = id
    self.config  = {}
    self.outputs = {}
    self.environment = None

    #: Echo :py:meth:`run()` output to terminal (output is always captured in :py:attr:`logfile`)
    self.verbose = False
    #: Stub :py:meth:`launch()` to skip execution of :py:meth:`run()`
    self.dry_run = False
    self.wrap_stdout = True

    self.working_directory = "./"
    self.max_label_length  = slogger.DEFAULT_LABEL_LENGTH
    self._launch_cmd       = action_launcher.__file__
    self.log_location      = None
    self._logfile          = f"{self.id}.log"
    self._state            = ActionState.INACTIVE
    self._status           = ActionStatus.NONE
    self._dependencies     = {}
    self._resources        = {}

    self.__exec_raw__      = True

    #: The start time of the :py:meth:`Action.launch()` in ISO format
    self.__timestamp__     = None
    # The elapsed time of the :py:meth:`Action.launch()`in seconds
    self.__time__          = None

    # This will be filled out by the time we pre_launch with any info the host provides
    self.__host_info__     = {}

    # These two are provided by the orchestrator upon begin setup
    # Use the run lock for mutually exclusive run logic (eg. clean logging)
    self._run_lock = None
    self.__wake__    = None

    super().__init__( filename=f"action_{id}", logname=id, base=Action )

  def save( self ) -> None:
    # Quickly remove sync objects then restore
    tmp_run_lock = self._run_lock
    tmp_wake     = self.__wake__
    self._run_lock = None
    self.__wake__  = None
    super().save()
    # Now restore
    self._run_lock = tmp_run_lock
    self.__wake__  = tmp_wake

  def __orch_wake__( self ) -> None:
    """Wake up the :py:class:`Orchestrator` from another thread.

    This should be used as an event trigger to induce re-evaluation of completed
    :py:class:`Actions <Action>` in the current workflow run.
    See :py:attr:`Orchestrator.__wake__` for more info.
    """
    if self.__wake__ is not None:
      self.__wake__.set()

  def _acquire( self ) -> None:
    """Acquire the shared :py:class:`Action` mutex.

    All :py:class:`Actions <Action>` in the current workflow have access to this mutex.
    """
    if self._run_lock is not None:
      self._run_lock.acquire()

  def _release( self ) -> None:
    """Release the shared :py:class:`Action` mutex."""
    if self._run_lock is not None:
      if self._run_lock.locked():
        self._run_lock.release()
      else:
        self.log( "Run lock already released", level=30 )

  @property
  def id( self ) -> str:
    """The unique ID of this :py:class:`Action`."""
    return self._id

  @property
  def state( self ) -> ActionState:
    """The current :py:class:`ActionState` of this :py:class:`Action`."""
    return self._state

  @property
  def status( self ) -> ActionStatus:
    """The current :py:class:`ActionStatus` of this :py:class:`Action`."""
    return self._status

  def set_state_pending( self ) -> None:
    """Quickset state to :py:attr:`ActionState.PENDING` and status to :py:attr:`ActionStatus.NONE`

    Typically set by the :py:class:`Orchestrator` during workflow startup
    """
    self._state  = ActionState.PENDING
    self._status = ActionStatus.NONE

  def set_state_error( self ) -> None:
    """Internal, only to report SANE errors"""
    self._state  = ActionState.ERROR
    self._status = ActionStatus.NONE

  def set_state_skipped( self ) -> None:
    """Quickset state to :py:attr:`ActionState.SKIPPED` and status to :py:attr:`ActionStatus.NONE`

    Set by the :py:class:`Orchestrator` during workflow running if deemed necessary
    """
    self._state  = ActionState.SKIPPED
    self._status = ActionStatus.NONE

  def set_status_success( self ) -> None:
    """Quickset state to :py:attr:`ActionState.FINISHED` and status to :py:attr:`ActionStatus.SUCCESS`

    Typically set by the :py:meth:`launch()` after :py:class:`Action` completion.
    """
    self._state  = ActionState.FINISHED
    self._status = ActionStatus.SUCCESS

  def set_status_failure( self ) -> None:
    """Quickset state to :py:attr:`ActionState.FINISHED` and status to :py:attr:`ActionStatus.FAILURE`

    Typically set by the :py:meth:`launch()` after :py:class:`Action` completion.
    """
    self._state  = ActionState.FINISHED
    self._status = ActionStatus.FAILURE

  @property
  def results( self ) -> dict:
    """Default results to be saved in the workflow cache returned as a ``dict``

    By default the following is returned

    .. parsed-literal::
        {
          "state"     : :py:attr:`state`, (string repr)
          "status"    : :py:attr:`status`, (string repr)
          "origins"   : :py:attr:`origins`,
          "outputs"   : :py:attr:`outputs`, (:py:meth:`dereferenced <dereference>`)
          "timestamp" : :py:attr:`__timestamp__`, (if available)
          "time"      : :py:attr:`__time__`, (if available)
        }

    When set, the provided ``dict`` should match the above format
    """
    results = {
                "state" : self.state.value,
                "status" : self.status.value,
                "origins" : self.origins,
                "outputs" : self.dereference( self.outputs, log=False, noexcept=True )
                }
    if self.state == ActionState.FINISHED:
      results["timestamp"] = self.__timestamp__
      results["time"]      = self.__time__
    return results

  @results.setter
  def results( self, results ):
    self._state  = ActionState( results["state"] )
    self._status = ActionStatus( results["status"] )
    self.outputs = results["outputs"]
    if self.state == ActionState.FINISHED:
      self.__timestamp__ = results["timestamp"]
      self.__time__      = results["time"]

  @property
  def host_info( self ) -> dict:
    """Info ``dict`` provided from the :py:attr:`~Orchestrator.current_host` using the :py:class:`Host.info`"""
    return self.__host_info__

  @property
  def info( self ) -> dict:
    """:py:class:`Action` info ``dict`` (:py:meth:`dereferenced <dereference>`) provided to direct
    dependencies via :py:attr:`dependencies` at runtime
    
    The default info ``dict`` provided is:

    .. parsed-literal::
        {
          "config"  : :py:attr:`config`,
          "outputs" : :py:attr:`outputs`
        }
    """
    return self.dereference( { "config" : self.config, "outputs" : self.outputs }, log=False, noexcept=True )

  @property
  def logfile( self ) -> str:
    """Absolute path to logfile capturing this :py:meth:`Action.run()` output"""
    if self.log_location is None:
      return None
    else:
      return os.path.abspath( f"{self.log_location}/{self._logfile}" )

  @property
  def dependencies( self ) -> dict:
    """A copy of the internal dependencies ``dict`` with relevant info about these direct dependencies

    The workflow uses a :math:`child \\rightarrow N parents` relation, where an :py:class:`Action`
    records which parent :py:class:`Actions <Action>` it is dependent on.

    Prior to workflow runtime, this ``dict`` contains parent :py:class:`Action` dependencies by
    :py:attr:`id` and their corresponding :py:class:`DependencyType` as ``"dep_type"`` in a sub-``dict``:

    .. parsed-literal::
        {
          "<parent-id-a>" : { "dep_type" : :py:class:`DependencyType` },
          "<parent-id-b>" : { "dep_type" : :py:class:`DependencyType` },
          ...
        }

    During runtime, this ``dict`` is modified to include the parent :py:attr:`Action.info` within
    the sub-``dict``. By default this would then allow access to dependencies' :py:attr:`outputs`
    and :py:attr:`config`:

    .. parsed-literal::
        {
          "<parent-id-a>" :
          {
            "dep_type" : :py:class:`DependencyType`,
            # The exact contents below come from :py:meth:`info()`
            "config"  : :py:attr:`config`,
            "outputs" : :py:attr:`outputs`
          },
          ...
        }
    """
    return self._dependencies.copy()

  def add_dependencies( self, *args : List[Union[str,Tuple[str,Union[str,DependencyType]]]] ) -> None:
    """Add dependencies to this :py:class:`Action`

    Use this function to properly add dependencies at any time before the workflow
    is run. This can be called before or after Actions are added to the workflow,
    but not after the workflow has started running. No checks for valid graph
    topology, dependency existing, and so on are performed. These checks are done
    by the :py:class:`Orchestrator` (see :py:meth:`Orchestrator.construct_dag`)

    Any number of dependencies may be listed as either :

    - **(a)** a single ``str`` corresponding to the dependency :py:attr:`id`
    - **(b)** tuple pair of ``str`` (dependency :py:attr:`id`) and

      - ``str`` representation of :py:class:`DependencyType`
      - :py:class:`DependencyType` value

    .. note:: If no :py:class:`DependencyType` is provided, i.e. calling in manner **(a)**,
              then the default is :py:attr:`DependencyType.AFTEROK`

    The following code block shows a few valid example calls:

    .. code-block:: python

        import sane

        @sane.register
        def register_actions( orch ):
          a = sane.Action( "a" )
          b = sane.Action( "bee" )
          c = sane.Action( "c" )

          orch.add_action( a )
          # The provided ID string MUST match the Action.id, not the object variable name
          #                    vvv
          a.add_dependencies( "bee", ( "c", "afterok" ) )
          b.add_dependencies( ( "c", sane.DependencyType.AFTEROK ) )
          # This is a valid call but does not form a valid DAG
          c.add_dependencies( "a" )

    :param args: variable length argument list with each entry corresponding to
                 a dependency
    :type args:  list[ str | tuple[ str, str | DependencyType ] ]
    """
    arg_idx = -1
    for arg in args:
      arg_idx += 1
      if isinstance( arg, str ):
        self._dependencies[arg] = { "dep_type" : DependencyType.AFTEROK }
      elif (
                isinstance( arg, tuple )
            and len(arg) == 2
            and isinstance( arg[0], str )
            and arg[1] in DependencyType ):
        self._dependencies[arg[0]] = { "dep_type" : DependencyType( arg[1] ) }
      else:
        msg  = f"Error: Argument {arg_idx} '{arg}' is invalid for {Action.add_dependencies.__name__}()"
        msg += f", must be of type str or tuple( str, DependencyType.value->str )"
        self.log( msg, level=50 )
        raise Exception( msg )

  def requirements_met( self, dependency_actions, resolve_locally ):
    met = RequirementsState.MET
    for dependency, dep_info in self._dependencies.items():
      action = dependency_actions[dependency]
      dep_met = _dependency_met( dep_info["dep_type"], action.state, action.status, submit_ok=not resolve_locally )
      if dep_met == RequirementsState.UNMET:
        msg  = f"Unmet dependency {dependency}, required {dep_info['dep_type']} "
        msg += f"but Action is {{{action.state.value}, {action.status.value}}}"
        self.log( msg )
      met = RequirementsState.reduce_state( met, dep_met )

    met = RequirementsState.reduce_state( met, self.extra_requirements_met( dependency_actions ) )
    return met

  # https://peps.python.org/pep-0484/#forward-references
  def extra_requirements_met( self, dependency_actions : Dict[str,"Action"] ) -> bool:
    """Check if any extra user-imposed requirements are met
    
    The return value may be ``True`` to signify this Action is ready to run, or
    ``False`` to note that a requirement was not satisfied and this action would not
    be able to run and thus be :py:attr:`~ActionState.SKIPPED`. Default is to always
    return ``True``

    .. caution:: For delayed requirements that may be fulfllled at a later time
                 (e.g. non-local host evaluation) refer to the source code for using
                 ``sane.action.RequirementState.PENDING``. If used, an external
                 entity (often a non-local host) **MUST** retrigger :py:attr:`Orchestrator.__wake__`
                 when this requirement may be affected to ensure the workflow does
                 not silently hang with the Action never running.

    :param dependency_actions: :py:class:`Actions` this instance is dependent on
    :type dependency_actions: dict[str, Action]
    """
    return True

  def _find_cmd( self, cmd, working_dir ):
    inpath = shutil.which( cmd ) is not None
    found_cmd = cmd

    if not inpath and not os.path.isabs( cmd ):
      found_cmd = os.path.abspath( os.path.join( working_dir, cmd ) )

    return found_cmd

  def resolve_path( self, input_path : str, base_path : str = None ) -> str:
    """Reslove a path using base path if input path is relative, otherwise only use input path

    :param input_path: relative or absolute path
    :param base_path:  base path to evaluate relative paths from
    :return: absolute path of ``input_path``
    """
    if base_path is None:
      base_path = self.working_directory

    if input_path is None:
      raise ValueError( f"Must provide a directory, input path : '{input_path}'" )

    output_path = base_path
    if os.path.isabs( input_path ):
      output_path = input_path
    else:
      # Evaluate relative path from passed in path
      output_path = os.path.abspath( os.path.join( base_path, input_path ) )
    return output_path

  def resolve_path_exists( self, input_path : str, base_path : str = None, allow_dry_run : bool = True ) -> str:
    """Wrapper on :py:meth:`resolve_path` to also check if that directory exists, throwing exception if not

    :param allow_dry_run: during dry runs do not fail if resolved path does not exist
    """
    resolved_path = self.resolve_path( input_path, base_path )
    if ( not self.dry_run or not allow_dry_run ) and not os.path.isdir( resolved_path ):
      raise NotADirectoryError( f"Provided path does not exist as directory : '{resolved_path}" )
    return resolved_path

  def file_exists_in_path( self, input_path : str, file : str, allow_dry_run : bool = True ):
    """Check if a specified file exists within a provided path

    :param input_path:    path to check for file evaluated from current working directory
    :param file:          regular file to check for
    :param allow_dry_run: during dry runs do not fail if resolved path does not exist
    """
    if ( not self.dry_run or not allow_dry_run ):
      f = os.path.join( input_path, file )
      if not os.path.isfile( f ):
        raise FileNotFoundError( f"File '{f}' not found" )
    else:
      return True

  def execute_subprocess(
                          self,
                          cmd : str,
                          arguments : list = None,
                          logfile : str = None,
                          verbose= False,
                          dry_run= False,
                          capture= False,
                          shell= False
                          ) -> tuple[int, str]:
    """Execution wrapper for running a command using :py:class:`subprocess.Popen`

    Notably, this wrapper handles:

    * command and argument aggregation
    * internal, logfile, and verbose logging with flushing in realtime
    * wrapping of stdout using internal log levels
    * returning return value along with captured stdout (if ``capture`` enabled)
    
    Prefer using this function if stdout log wrapping is desired. If none of the
    features above are of use, any subprocess function call can be used, but may
    or may not appear in the log output as desired. All output is logged, however.

    :param cmd:       command to execute
    :param arguments: list of arguments, will be ``str`` cast
    :param logfile:   optional logfile to write command output to
    :param verbose:   optional output the command stdout and stderr to terminal
    :param dry_run:   optional do not call :py:class:`subprocess.Popen`, i.e. stub this call
    :param capture:   optional capture stderr/stdout to ``str`` return
    :param shell:     optional treat execution as shell command (see :py:class:`subprocess.Popen` for more detail)
    :return: ``tuple`` of execution return value and any stderr/stdout capture
    """
    args = [cmd]

    if arguments is not None:
      args.extend( arguments )

    args = [ str( arg ) for arg in args ]

    command = " ".join( [ arg if " " not in arg else "\"{0}\"".format( arg ) for arg in args ] )
    self._acquire()
    self.log( "Running command:" )
    self.log( "  {0}".format( command ) )
    self._release()

    retval  = -1
    content = None

    if not dry_run:
      ############################################################################
      ##
      ## Call subprocess
      ##
      # https://stackoverflow.com/a/18422264
      if verbose:
        self.log( "Command output will be printed to this terminal" )
      if logfile is not None:
        self.log( "Command output will be captured to logfile {0}".format( logfile ) )

      # Keep a duplicate of the output as well in memory as a string
      output = None
      if capture:
        output = io.BytesIO()

      if shell:
        args = " ".join( args )

      proc = subprocess.Popen(
                              args,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              shell=shell
                              )

      logfileOutput = None
      if logfile is not None:
        logfileOutput = open( logfile, "w+", buffering=1 )

      # Temporarily swap in a very crude logger
      log = lambda *args: self.log( *args, level=25 )
      if self.__exec_raw__:
        log = lambda msg: slogger.logger.getChild( "raw" ).log( 25, msg )

      for c in iter( lambda: proc.stdout.readline(), b"" ):
        # Always store in logfile if possible
        if logfileOutput is not None:
          logfileOutput.write( c.decode( 'utf-8', 'replace' ) )
          logfileOutput.flush()

        if capture:
          output.write( c )

        # Also duplicate output to stdout if requested
        if verbose:
          # Use a raw logger to ensure this also gets captured by the logging handlers
          log( c.decode( 'utf-8', 'replace' ).rstrip( "\n" ) )
          # print( c.decode( 'utf-8', 'replace' ), flush=True, end="" )
          # sys.stdout.buffer.write(c)
          # sys.stdout.flush()

      # We don't mind doing this as the process should block us until we are ready to continue
      dump, err    = proc.communicate()
      retval       = proc.returncode

      if logfile is not None:
        logfileOutput.close()
      ##
      ##
      ##
      ############################################################################
    else:
      self.log( "Doing dry-run, no ouptut" )
      retval = 0
      output = "12345"

    # self.log( "\n" )
    # print( "\n", flush=True, end="" )

    if not dry_run:
      if capture:
        if False:  # TODO Not sure which conditional is supposed to lead here
          output.seek(0)
          content = output.read()
        else:
          content = output.getvalue().decode( 'utf-8' )
        output.close()
    else:
      content = output

    return retval, content

  def launch( self, working_directory : str, launch_wrapper : Tuple[str, list] = None ) -> Tuple[int, str]:
    """Main entry point for executing an :py:class:`Action` within a workflow

    Coordinates the current state and status of the action whilst executing, prepares
    the :py:class:`Action` for :ref:`action_launcher.py` execution proxy, and
    adjust call to :py:meth:`execute_subprocess` if a ``launch_wrapper`` is provided.

    :py:attr:`__timestamp__` and total execution :py:attr:`__time__` are recorded immediately
    at the beginning and end of this function, not just around the :py:meth:`execute_subprocess()`
    call.

    The order of operations, as they concern the user, are:

      #. :py:meth:`pre_launch()` (shared :py:class:`Action` mutex locked around this call)
      #. :py:meth:`save()`
      #. resolve internal launch command (:ref:`action_launcher.py`) and ``launch_wrapper``
      #. :py:meth:`execute_subprocess()` of resolved command, capturing to :py:attr:`logfile` and using :py:attr:`verbose` and :py:attr:`dry_run`
      #. final :py:attr:`state` and :py:attr:`status` recorded
      #. :py:meth:`post_launch()` called with output of (4) (shared :py:class:`Action` mutex locked around this call)
      #. :py:meth:`__orch_wake__` the :py:class:`Orchestrator`
      #. return output of (4)

    If an unexpected ``Exception`` occurs at any point outside of the :py:class:`subprocess.Popen`
    call within :py:meth:`execute_subprocess()`, the following occurs:

      #. :py:meth:`set_state_error()` called
      #. shared :py:class:`Action` mutex force unlocked
      #. :py:meth:`__orch_wake__` the :py:class:`Orchestrator`
      #. re-raise the same ``Exception``

    .. danger:: Avoid modifying or overriding this function in any derived :py:class:`Action`

    :param working_directory: Base directory to evaluate :py:attr:`working_directory` from.
                              Final resolved path is used to evaluate the internal ``_launch_cmd``
                              or ``launch_wrapper`` command, if provided.
    :param launch_wrapper:    ``tuple`` pair of command and list of arguments to use as a prefix to
                              :py:meth:`execute_subprocess()` where this command is the new command
                              and the arguments, then previous command and arguments are provided in
                              that order.
    :type  launch_wrapper:    tuple[str, list[str]]
    :return: ``tuple`` of :py:meth:`execute_subprocess()` of this Action's :py:meth:`run()`
             (or ``launch_wrapper`` output if provided)
    :rtype: tuple[int,str]
    """
    try:
      self.__timestamp__ = datetime.datetime.now().replace( microsecond=0 ).isoformat()
      start_time = time.perf_counter()
      self.label_length = self.max_label_length
      thread_name = threading.current_thread().name
      logname     = self.id
      if thread_name is not None:
        logname = "{0:<10} [{1}".format( f"{thread_name}]", self.id )
      self.logname = logname

      self.push_logscope( "launch" )
      self._acquire()
      ok = self.pre_launch()
      self._release()
      if ok is not None and not ok:
        raise AssertionError( "pre_launch() returned False" )

      # Set current state of this instance
      self._state = ActionState.RUNNING
      self._status = ActionStatus.NONE

      # Immediately save the current state of this action
      self.log( "Saving action information for launch..." )
      self.label_length = slogger.DEFAULT_LABEL_LENGTH
      self.logname = self.id
      self.save()
      self.label_length = self.max_label_length
      self.logname = logname

      # Self-submission of execute, but allowing more complex handling by re-entering into this script
      action_dir = self.resolve_path( self.working_directory, working_directory )

      self.log( f"Using working directory : '{action_dir}'" )

      cmd = self._find_cmd( self._launch_cmd, action_dir )
      args = [ action_dir, self.save_file ]
      # python wheel build strips executable attribute and there's no recourse that
      # keeps it in the package directory, so launch it with python3
      if os.path.splitext( cmd )[1] == ".py" and not os.access( action_launcher.__file__, os.X_OK ):
        args.insert( 0, cmd )
        cmd = "python3"

      if launch_wrapper is not None:
        args.insert( 0, cmd )
        cmd = self._find_cmd( launch_wrapper[0], action_dir )
        args[:0] = launch_wrapper[1]

      retval = -1
      content = ""

      if self._logfile is None and not self.verbose:
        self._acquire()
        self.log( "Action will not be printed to screen or saved to logfile", level=30 )
        self.log( "Consider modifying the action to use one of these two options", level=30 )
        self._release()
      retval, content = self.execute_subprocess(
                                                cmd,
                                                args,
                                                logfile=self.logfile,
                                                capture=True,
                                                verbose=self.verbose,
                                                dry_run=self.dry_run
                                                )

      self._state = ActionState.FINISHED
      if retval != 0:
        self._status = ActionStatus.FAILURE
      else:
        if launch_wrapper is None:
          self._status = ActionStatus.SUCCESS
        else:
          # No idea what the wrapper might do, this is our best guess
          self._status = ActionStatus.SUBMITTED

      self._acquire()
      ok = self.post_launch( retval, content )
      self._release()
      if ok is not None and not ok:
        raise AssertionError( "post_launch() returned False" )

      # notify we have finished
      if thread_name is not None:
        self.logname = self.id
      self.pop_logscope()
      self.__orch_wake__()
      self.__time__ = "{:.6f}".format( time.perf_counter() - start_time )
      return retval, content
    except Exception as e:
      # We failed :( still notify the orchestrator
      self.set_state_error()
      self._release()
      self.log( f"Exception caught, cleaning up : {e}", level=40 )
      self.logname = self.id
      self.label_length = slogger.DEFAULT_LABEL_LENGTH
      self.pop_logscope()
      self.__orch_wake__()
      self.__time__ = "{:.6f}".format( time.perf_counter() - start_time )
      raise e

  def ref_string( self, input_str ):
    return len( list( Action.REF_RE.finditer( input_str ) ) ) > 0

  def dereference_str( self, input_str : str, log=True, noexcept=False ) -> str:
    """Dereference an input string using GitHub Actions style syntax scoped to the current object
    
    Continuously dereferences strings within the current object until no more 
    substitutions can be made. All attributes and properties can be referenced,
    but dereferencing will work best with attributes that are ``dict``, ``list``,
    ``str``, or ``int`` values.
    
    | Nested referencing can be achieved with ``.`` operator (key as next field)
    | Index referencing can be achieved with ``[]`` operator (positive integer)

    Valid syntax examples:

    .. code-block:: python

        action_a = sane.Action( "action_a" )
        action_b = sane.Action( "action_b" )
        action_a.add_dependencies( "action_b" )

        action_a.config["foo"] = "1"
        action_a.config["bar"] = "2"
        action_a.config["zoo"] = [ 3, 4 ]
        action_a.config["boo"] = 7
        action_a.config["moo"] = { "loo" : [ { "goo" : "5", "hoo" : [ 6, "${{ config.boo" }} ] }, 0, 0, 0 ] }
        action_a.outputs["outfile"] = "something"
        action_a.add_resource_requirements( { "cpus" : 12, "mem" : "1gb" } )

        action_b.outputs["some_file"] = "fill_this_in"

        # Within the context of action_a these are valid
        "${{ config.foo }}"       => "1"
        "${{ config.bar }}"       => "2"
        "${{ config.zoo[1] }}"    => "4"
        "${{ resources.cpus }}"   => "12"
        "${{ outputs.outfile }}"  => "something"
        # At runtime this would be valid, with this value if the value in action_b has not changed
        "${{ dependencies.action_b.outputs.some_file }}" => "fill_this_in"

        # A complex dereference
        "${{ config.moo.loo[0].hoo[1] }}" => "7"

    .. attention:: During the substitution, if indexing to the next attribute yields ``None`` an
                   ``Exception`` will be thrown. Thus, at the time of dereferencing, the string
                   input **MUST** be valid.

    :param log:      enable logging
    :param noexcept: disable exceptions and instead allow failed dereference
    :return: string fully dereferenced
    """
    curr_matches = list( Action.REF_RE.finditer( input_str ) )
    prev_matches = None
    output_str = input_str

    def matches_equal( lhs, rhs ):
      if lhs is None and rhs is not None or rhs is None and lhs is not None:
        return False
      if len( lhs ) != len( rhs ):
        return False
      for i in range( len( lhs ) ):
        if lhs[i].span() != rhs[i].span():
          return False
        if lhs[i].groupdict() != rhs[i].groupdict():
          return False
      return True

    # Fully dereference as much as possible
    while not matches_equal( prev_matches, curr_matches ):
      prev_matches = curr_matches
      for match in curr_matches:
        substr = match.group( "substr" )
        attrs  = match.group( "attrs" )

        curr = self
        for attr in attrs.split( "." ):
          attr_groups = Action.IDX_RE.fullmatch( attr ).groupdict()
          get_attr = None
          if isinstance( curr, dict ):
            get_attr = curr.get
          else:
            get_attr = lambda x: getattr( curr, x, None )

          curr = get_attr( attr_groups["attr"] )

          ########################################################################
          # Special cases
          if callable( curr ):
            if attr == "resources" and "name" in self.host_info:
              curr = curr( self.host_info["name"] )
            else:
              curr = curr()
          ########################################################################
          if curr is None:
            msg = f"Dereferencing yielded None for '{attr_groups['attr']}' in '{substr}'"
            if noexcept:
              # field not present
              if log:
                self.log( msg, level=30 )
              return output_str
            else:
              msg = f"Dereferencing yielded None for '{attr_groups['attr']}' in '{substr}'"
              self.log( msg, level=40 )
              raise Exception( msg )
          

          if attr_groups["idx"] is not None:
            curr = curr[ int(attr_groups["idx"]) ]
        output_str = output_str.replace( substr, str( curr ) )

      curr_matches = list( Action.REF_RE.finditer( output_str ) )

    if output_str != input_str and log:
      self.log( f"Dereferenced '{input_str}'" )
      self.log( f"     into => '{output_str}'" )
    return output_str

  def dereference( self, obj, log=True, noexcept=False ):
    """Fully dereference all strings within the ``obj`` passed in
    
    For ``dict`` and ``list`` objects, each will be iterated over and this function
    will be recursively call for each iterated value (not key), and then assigned
    back to itself, presumably modified. For ``str`` objects :py:meth:`dereference_str()`
    will be called. 

    For all other object types, the ``obj`` will be unmodified.

    The ``obj`` is then returned, modified if necessary (and possible) to contain
    only fully dereferenced strings.

    :return: ``obj`` with all strings :py:meth:`dereferenced <dereference_str>`
    """
    if isinstance( obj, dict ):
      for key in obj.keys():
        output = self.dereference( obj[key], log=log, noexcept=noexcept )
        if output is not None:
          obj[key] = output
      return obj
    elif isinstance( obj, list ):
      for i in range( len( obj ) ):
        output = self.dereference( obj[i], log=log, noexcept=noexcept )
        if output is not None:
          obj[i] = output
      return obj
    elif isinstance( obj, str ):
      return self.dereference_str( obj, log=log, noexcept=noexcept )
    else:
      return obj

  def pre_launch( self ) -> None:
    """Called before :py:meth:`save()` and execution of ``action_launcher.py``. See :py:meth:`launch`"""
    pass

  def post_launch( self, retval, content ) -> bool:
    """Called after execution of ``action_launcher.py`` with the output of :py:meth:`execute_subprocess()`. See :py:meth:`launch`

    :return: If return is ``False``, :py:class:`Action` is assumed to have a :py:attr:`~ActionStatus.FAILURE`
    """
    pass

  def pre_run( self ) -> None:
    """Called just before :py:meth:`run()` within the context of the Action subprocess"""
    pass

  def post_run( self, retval ) -> None:
    """Called just after :py:meth:`run()` within the context of the Action subprocess"""
    pass

  def run( self ) -> int:
    """The main execution of the :py:class:`Action`, performed within an isolated subprocess

    This function will be called from within ``action_launcher.py`` under an isolated
    subprocess with the requested :py:attr:`environment` already :py:meth:`~Environment.setup`.

    Users may override this function in a derived :py:class:`Action` as primary way
    to change how an :py:class:`Action` runs. The default implementation of this
    function fully :py:meth:`dereferences <dereference>` the :py:attr:`config`
    ``dict`` and executes ``config["command"]`` and ``config["arguments"]`` in
    another subprocess via :py:meth:`execute_subprocess`.

    .. hint:: The subprocess of running ``config["command"]`` in the default implementation
              of this function will inherit the :py:meth:`Environment.setup` settings.
              See :py:class:`subprocess.Popen` ``env=None`` for more info.

    :return: The return value of running this action. Used by ``action_launcher.py``
             as the ``exit()`` code. Thus, anything aside from ``0`` is :py:attr:`~ActionStatus.FAILURE`.
             The default returns the return value of :py:meth:`execute_subprocess`
             from running ``config["command"]``
    """
    self.push_logscope( "run" )
    # Users may overwrite run() in a derived class, but a default will be provided for config-file based testing (TBD)
    # The default will simply launch an underlying command using a subprocess
    self.dereference( self.config )

    command = None
    if "command" in self.config:
      command = self._find_cmd( self.config["command"], "./" )

    if command is None:
      self.log( "No command provided for default Action" )
      exit( 1 )

    arguments = None
    if "arguments" in self.config:
      arguments = self.config["arguments"]

    retval, content = self.execute_subprocess( command, arguments, verbose=True, capture=False )
    self.pop_logscope()
    return retval

  def __str__( self ):
    return f"Action({self.id})"

  @copydoc( jconfig.JSONConfig.load_core_config, append=False )
  @copydoc( res.ResourceRequestor.load_core_config )
  def load_core_config( self, config, origin ):
    """Load :py:class:`Action` settings from the provided config dict, all keys are optional.

    The following keys are loaded verbatim into their respective attribute:

    * ``"environment"`` => :py:attr:`environment`
    * ``"working_directory"`` => :py:attr:`working_directory`

    The following key is loaded and calls :py:func:`~json_config.recursive_update`
    preserve any unmodified existing values:

    * ``"config"`` => :py:attr:`config`
    
    The following key is loaded directly to :py:meth:`add_dependencies` as key-value
    tuple pairs via :py:meth:`dict.items()`

    * ``"dependencies"``

    An example input config:

    .. parsed-literal::

        {
          "environment" : "gnu",
          # Recall that :py:attr:`config` is a generic ``dict``
          "config"      : { "foo" : [ 1, 2, 3 ], "bar" : "file" },
          # if loading via plain-text (e.g. JSON), use the text value
          # of :py:class:`DependencyType` as noted in :py:meth:`add_dependencies`
          "dependencies" : { "action_b" : "afterok", "action_c" : "afternotok" }
        }
    """
    environment = config.pop( "environment", None )
    if environment is not None:
      self.environment = environment

    dir = config.pop( "working_directory", None )
    if dir is not None:
      self.working_directory = dir

    act_config = config.pop( "config", None )
    if act_config is not None:
      jconfig.recursive_update( self.config, act_config )

    self.add_dependencies( *config.pop( "dependencies", {} ).items() )

    super().load_core_config( config, origin )
