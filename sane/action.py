import os
import json
import shutil
import sys
import io
import subprocess
from enum import Enum, EnumMeta

import sane.save_state as state
import sane.json_config as jconfig
import sane.action_launcher as action_launcher


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


class ActionStatus( Enum ):
  SUCCESS   = "success"
  FAILURE   = "failure"
  SUBMITTED = "submitted"
  NONE      = "none"


def _dependency_met( dep_type, state, status ):
  if dep_type != DependencyType.AFTER:
    if state == ActionState.FINISHED:
      if dep_type == DependencyType.AFTERANY:
        return True
      else:
        # Writing out the checks explicitly, submitted is an ambiguous state and
        # so can count for both... maybe this should be reconsidered later
        if dep_type == DependencyType.AFTEROK:
          return status == ActionStatus.SUCCESS or status == ActionStatus.SUBMITTED
        elif dep_type == DependencyType.AFTERNOTOK:
          return status == ActionStatus.FAILURE or status == ActionStatus.SUBMITTED
  elif dep_type == DependencyType.AFTER:
    if state == ActionState.RUNNING or state == ActionState.FINISHED:
      return True
  # Everything else
  return False


class Action( state.SaveState, jconfig.JSONConfig ):
  CONFIG_TYPE = "Action"

  def __init__( self, id ):
    self._id = id
    self.config = {}
    self.environment = None
    self.local = None

    self.verbose = False
    self.dry_run = False
    self._launch_cmd       = action_launcher.__file__
    self.log_location      = None
    self._logfile          = f"{self.id}.log"
    self._state            = ActionState.INACTIVE
    self._status           = ActionStatus.NONE
    self._dependencies     = {}
    self._resources        = {}
    self.timelimit         = None

    super().__init__( name=id, filename=f"action_{id}", base=Action )

  @property
  def id( self ):
    return self._id

  @property
  def state( self ):
    return self._state

  def set_state_pending( self ):
    self._state  = ActionState.PENDING
    self._status = ActionStatus.NONE

  @property
  def status( self ):
    return self._status

  @property
  def logfile( self ):
    if self.log_location is None:
      return None
    else:
      return os.path.abspath( f"{self.log_location}/{self._logfile}" )

  @property
  def resources( self ):
    return self._resources.copy()

  @property
  def dependencies( self ):
    return self._dependencies.copy()

  def add_dependencies( self, *args ):
    arg_idx = -1
    for arg in args:
      arg_idx += 1
      if isinstance( arg, str ):
        self._dependencies[arg] = DependencyType.AFTEROK
      elif (
                isinstance( arg, tuple )
            and len(arg) == 2 
            and isinstance( arg[0], str )
            and arg[1] in DependencyType ):
        self._dependencies[arg[0]] = DependencyType( arg[1] )
      else:
        msg  = f"Error: Argument {arg_idx} '{arg}' is invalid for {Action.add_dependencies.__name__}()"
        msg += f", must be of type str or tuple( str, DependencyType.value->str )"
        self.log( msg )
        raise Exception( msg )

  def requirements_met( self, dependency_actions ):
    met = True
    for dependency, dep_type in self._dependencies.items():
      action = dependency_actions[dependency]
      dep_met = _dependency_met( dep_type, action.state, action.status )
      if not dep_met:
        msg  = f"Unmet dependency {dependency}, required {dep_type} "
        msg += f"but Action is {{{action.state}, {action.status}}}"
        self.log( msg )
      met = ( met and dep_met )

    met = met and self.extra_requirements_met( dependency_actions )
    return met

  def extra_requirements_met( self, dependency_actions ):
    return True

  def execute_subprocess( self, cmd, arguments=None, logfile=None, verbose=False, dry_run=False, capture=False ):
    args = [cmd]
    inpath = shutil.which( cmd ) is not None
    if not inpath:
      args[0] = os.path.abspath( cmd )

    if arguments is not None:
      args.extend( arguments )

    args = [ str( arg ) for arg in args ]

    command = " ".join( [ arg if " " not in arg else "\"{0}\"".format( arg ) for arg in args ] )
    self.log( "Running command:" )
    self.log( "  {0}".format( command ) )

    retval  = -1
    content = None

    # if self.verbose:
    #   self.log(  "*" * 15 + "{:^15}".format( "START launch " + self.id ) + "*" * 15 )
    # if self.verbose:
    #   self.log(  "*" * 15 + "{:^15}".format( "STOP launch " + self.id ) + "*" * 15 )

    # Temporarily create a very crude logger
    log_raw = self._logger.getChild( "raw" )

    if not dry_run:
      ############################################################################
      ##
      ## Call subprocess
      ##
      # https://stackoverflow.com/a/18422264
      if logfile is not None and verbose:
        self.log( "Local step will also be captured to logfile {0}".format( logfile ) )

      # Keep a duplicate of the output as well in memory as a string
      output = None
      if capture:
        output = io.BytesIO()

      proc = subprocess.Popen(
                              args,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT
                              )

      logfileOutput = None
      if logfile is not None:
        logfileOutput = open( logfile, "w+", buffering=1 )

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
          log_raw.info( c.decode( 'utf-8', 'replace' ).rstrip( "\n" ) )
          # print( c.decode( 'utf-8', 'replace' ), flush=True, end="" )
          # sys.stdout.buffer.write(c)
          # sys.stdout.flush()

      # We don't mind doing this as the process should block us until we are ready to continue
      dump, err    = proc.communicate()
      retval       = proc.returncode
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
    self.pre_launch()
    # Set current state of this instance
    self._state = ActionState.RUNNING
    self._status = ActionStatus.NONE

    # Immediately save the current state of this action
    self.save()

    # Self-submission of execute, but allowing more complex handling by re-entering into this script
    cmd = self._launch_cmd
    args = [ working_directory, self.save_file ]
    if launch_wrapper is not None:
      args.prepend( cmd )
      cmd = launch_wrapper[0]
      args[:0] = launch_wrapper[1]

    retval = -1
    content = ""
    try:
      if self._logfile is None and not self.verbose:
        self.log( "Action will not be printed to screen or saved to logfile" )
        self.log( "Consider modifying the action to use one of these two options" )
      retval, content = self.execute_subprocess(
                                                cmd,
                                                args,
                                                logfile=self.logfile,
                                                capture=True,
                                                verbose=self.verbose,
                                                dry_run=self.dry_run
                                                )

      # if need to submit
      #   get job id from content

      # Communicate up the chain
    except Exception as e:
      # Communicate up the chain that we failed :(

      # and propagate
      raise e

    self._state = ActionState.FINISHED
    if retval != 0:
      self._status = ActionStatus.FAILURE
    else:
      # If HPC type submission
      # self._status = ActionStatus.SUBMITTED
      self._status = ActionStatus.SUCCESS
    self.post_launch( retval, content )
    return retval, content

  def setup( self ):
    pass

  def pre_launch( self ):
    pass

  def post_launch( self, retval, content ):
    pass

  def run( self ):
    # Users may overwrite run() in a derived class, but a default will be provided for config-file based testing (TBD)
    # The default will simply launch an underlying command using a subprocess
    command = None
    if "command" in self.config:
      command = self.config["command"]

    if command is None:
      self.log( "No command provided for default Action" )
      exit( 1 )

    arguments = None
    if "arguments" in self.config:
      arguments = self.config["arguments"]

    retval, content = self.execute_subprocess( command, arguments, verbose=True )
    return retval

  def __str__( self ):
    return f"Action({self.id})"

  def load_core_config( self, config ):
    environment = config.pop( "environment", None )
    if environment is not None:
      self.environment = environment

    timelimit = config.pop( "timelimit", None )
    if timelimit is not None:
      self.timelimit = timelimit

    local = config.pop( "local", None )
    if local is not None:
      self.local = local

    act_config = config.pop( "config", None )
    if act_config is not None:
      self.config = act_config

    self.add_dependencies( *config.pop( "dependencies", {} ).items() )

    self.add_resource_requirements( config.pop( "resources", {} ) )

  def add_resource_requirements( self, resource_dict ):
    for resource, info in resource_dict.items():
      if resource in self._resources:
        self.log( f"Resource '{resource}' already set, ignoring new resource setting", level=30 )
      else:
        self._resources[resource] = str(info)
