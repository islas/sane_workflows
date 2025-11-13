import os
import shutil
import re
import io
import subprocess
import threading
import datetime
import time
from enum import Enum, EnumMeta

import sane.logger as slogger
import sane.save_state as state
import sane.json_config as jconfig
import sane.action_launcher as action_launcher
import sane.resources as res


class ValueMeta( EnumMeta ):
  def __contains__( cls, item ):
    try:
      cls( item )
    except ValueError:
      return False
    return True


class DependencyType( str, Enum, metaclass=ValueMeta ):
  AFTEROK    = "afterok"     # after successful run (this is the default)
  AFTERNOTOK = "afternotok"  # after failure
  AFTERANY   = "afterany"    # after either failure or success
  AFTER      = "after"       # after the step *starts*

  def __str__( self ):
    return str( self.value )

  def __repr__( self ):
    return str( self.value )


class ActionState( Enum ):
  PENDING  = "pending"
  RUNNING  = "running"
  FINISHED = "finished"
  INACTIVE = "inactive"
  SKIPPED  = "skipped"
  ERROR    = "error"    # This should not be used for errors in running the action (status),
                        # Instead this should be reserved for internal errors of the action

  @classmethod
  def valid_run_state( cls, state ):
    return state == cls.PENDING or state == cls.RUNNING


class ActionStatus( Enum ):
  SUCCESS   = "success"
  FAILURE   = "failure"
  SUBMITTED = "submitted"
  NONE      = "none"


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
  CONFIG_TYPE = "Action"
  REF_RE = re.compile( r"(?P<substr>[$]{{[ ]*(?P<attrs>(?:\w+(?:\[\d+\])?\.)*\w+(?:\[\d+\])?)[ ]*}})" )
  IDX_RE = re.compile( r"(?P<attr>\w+)(?:\[(?P<idx>\d+)\])?" )

  def __init__( self, id ):
    self._id = id
    self.config  = {}
    self.outputs = {}
    self.environment = None

    self.verbose = False
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
    self._host_resources   = {}

    self.__exec_raw__      = True
    self.__timestamp__     = None
    self.__time__          = None

    # This will be filled out by the time we pre_launch with any info the host provides
    self.__host_info__     = {}

    # These two are provided by the orchestrator upon begin setup
    # Use the run lock for mutually exclusive run logic (eg. clean logging)
    self._run_lock = None
    # This is to be used to wake the orchestrator only when the action has completed
    self.__wake__    = None

    super().__init__( filename=f"action_{id}", logname=id, base=Action )

  def save( self ):
    # Quickly remove sync objects then restore
    tmp_run_lock = self._run_lock
    tmp_wake     = self.__wake__
    self._run_lock = None
    self.__wake__  = None
    super().save()
    # Now restore
    self._run_lock = tmp_run_lock
    self.__wake__  = tmp_wake

  def __orch_wake__( self ):
    if self.__wake__ is not None:
      self.__wake__.set()

  def _acquire( self ):
    if self._run_lock is not None:
      self._run_lock.acquire()

  def _release( self ):
    if self._run_lock is not None:
      if self._run_lock.locked():
        self._run_lock.release()
      else:
        self.log( "Run lock already released", level=30 )

  @property
  def id( self ):
    return self._id

  @property
  def state( self ):
    return self._state

  def set_state_pending( self ):
    self._state  = ActionState.PENDING
    self._status = ActionStatus.NONE

  def set_status_success( self ):
    self._state  = ActionState.FINISHED
    self._status = ActionStatus.SUCCESS

  def set_status_failure( self ):
    self._state  = ActionState.FINISHED
    self._status = ActionStatus.FAILURE

  def set_status_error( self ):
    self._state  = ActionState.ERROR
    self._status = ActionStatus.NONE

  def set_status_skipped( self ):
    self._state  = ActionState.SKIPPED
    self._status = ActionStatus.NONE

  @property
  def status( self ):
    return self._status

  @property
  def results( self ):
    results = {
                "state" : self.state.value,
                "status" : self.status.value,
                "origins" : self.origins,
                "outputs" : self.dereference( self.outputs, log=False )
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
  def host_info( self ):
    return self.__host_info__

  @property
  def info( self ):
    return self.dereference( { "config" : self.config, "outputs" : self.outputs }, log=False )

  @property
  def logfile( self ):
    if self.log_location is None:
      return None
    else:
      return os.path.abspath( f"{self.log_location}/{self._logfile}" )

  @property
  def dependencies( self ):
    return self._dependencies.copy()

  def add_dependencies( self, *args ):
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

  def extra_requirements_met( self, dependency_actions ):
    return True

  def _find_cmd( self, cmd, working_dir ):
    inpath = shutil.which( cmd ) is not None
    found_cmd = cmd

    if not inpath and not os.path.isabs( cmd ):
      found_cmd = os.path.abspath( os.path.join( working_dir, cmd ) )

    return found_cmd

  def resolve_path( self, input_path, base_path=None ):
    """reslove a path using base path if input path is relative, otherwise only use input path"""
    if base_path is None:
      base_path = self.working_directory

    output_path = base_path
    if os.path.isabs( input_path ):
      output_path = input_path
    else:
      # Evaluate relative path from passed in path
      output_path = os.path.abspath( os.path.join( base_path, input_path ) )
    return output_path

  def resolve_path_exists( self, input_path, base_path=None, allow_dry_run=True ):
    """Wrapper on resolve_path to also check if that directory exists"""
    if base_path is None:
      base_path = self.working_directory

    if input_path is None:
      raise ValueError( f"Must provide a directory, input path : '{input_path}'" )
    # Immediately resolve from working directory, this assumes we run from the
    # root of WRF repo
    resolved_path = self.resolve_path( input_path, base_path )
    if ( not self.dry_run or not allow_dry_run ) and not os.path.isdir( resolved_path ):
      raise NotADirectoryError( f"Provided path does not exist as directory : '{resolved_path}" )
    return resolved_path

  def file_exists_in_path( self, input_path, file, allow_dry_run=True ):
    if ( not self.dry_run or not allow_dry_run ):
      f = os.path.join( input_path, file )
      if not os.path.isfile( f ):
        raise FileNotFoundError( f"File '{f}' not found" )
    else:
      return True

  def execute_subprocess( self, cmd, arguments=None, logfile=None, verbose=False, dry_run=False, capture=False, shell=False ):
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

  def launch( self, working_directory, launch_wrapper=None ):
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
      self.set_status_error()
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

  def dereference_str( self, input_str, log=True ):
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

  def dereference( self, obj, log=True ):
    if isinstance( obj, dict ):
      for key in obj.keys():
        output = self.dereference( obj[key], log=log )
        if output is not None:
          obj[key] = output
      return obj
    elif isinstance( obj, list ):
      for i in range( len( obj ) ):
        output = self.dereference( obj[i], log=log )
        if output is not None:
          obj[i] = output
      return obj
    elif isinstance( obj, str ):
      return self.dereference_str( obj, log=log )
    else:
      return obj

  def pre_launch( self ):
    pass

  def post_launch( self, retval, content ):
    pass

  def pre_run( self ):
    pass

  def post_run( self, retval ):
    pass

  def run( self ):
    self.push_logscope( "::run" )
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

  def load_core_config( self, config, origin ):
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
