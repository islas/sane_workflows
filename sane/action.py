import os
import json
import shutil
import sys
import io
import subprocess
from enum import Enum

import sane.save_state as state
import sane.json_config as jconfig


class DependencyType( str, Enum ):
  AFTEROK    = "afterok"     # after successful run (this is the default)
  AFTERNOTOK = "afternotok"  # after failure
  AFTERANY   = "afterany"    # after either failure or success
  AFTER      = "after"       # after the step *starts*

  def __str__( self ):
    return str( self.value )

  def __repr__( self ):
    return str( self.value )

  @classmethod
  def __contains__(cls, item):
    try:
      cls(item)
    except ValueError:
      return False
    return True



class ActionState( Enum ):
  PENDING  = 0
  RUNNING  = 1
  FINISHED = 2
  INACTIVE = 3
  ERROR    = 4  # This should not be used for errors in running the action (status),
                # Instead this should be reserved for internal errors of the action


class Action( state.SaveState, jconfig.JSONConfig ):
  CONFIG_TYPE = "Action"

  def __init__( self, id ):
    self._id = id
    self.config = {}
    self.environment = None

    self._verbose = False
    self._dry_run = False

    self._logfile          = None
    self._state            = ActionState.INACTIVE
    self._dependencies     = {}

    super().__init__( name=id, filename=f"action_{id}", base=Action )

  @property
  def id( self ):
    return self._id

  @property
  def state( self ):
    return self._state

  @property
  def dependencies( self ):
    return self._dependencies.copy()

  def add_dependencies( self, *args ):
    arg_idx = -1
    for arg in args:
      arg_idx += 1
      if isinstance( arg, str ):
        self._dependencies[arg] = DependencyType.AFTEROK
      elif isinstance( arg, tuple ) and len(arg) == 2 and isinstance( arg[0], str ) and arg[1] in DependencyType:
        self._dependencies[arg[0]] = DependencyType[arg[1]]
      else:
        msg  = f"Error: Argument {arg_idx} '{arg}' is invalid for {Action.add_dependencies.__name__}()"
        msg += f", must be of type str or tuple( str, DependencyType.value->str )"
        self.log( msg )
        raise Exception( msg )

  def execute_subprocess( self, cmd, arguments=None, logfile=None, verbose=False, dry_run=False, capture=False ):
    args = [cmd]
    inpath = shutil.which( cmd ) is not None
    if not inpath:
      args[0] = os.path.abspath( cmd )

    if arguments is not None:
      args.extend( arguments )

    command = " ".join( [ arg if " " not in arg else "\"{0}\"".format( arg ) for arg in args ] )
    self.log( "Running command:" )
    self.log( "  {0}".format( command ) )

    retval  = -1
    content = None


    # if self._verbose:
    #   self.log(  "*" * 15 + "{:^15}".format( "START launch " + self.id ) + "*" * 15 )
    # if self._verbose:
    #   self.log(  "*" * 15 + "{:^15}".format( "STOP launch " + self.id ) + "*" * 15 )


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

      for c in iter( lambda: proc.stdout.read(1), b"" ):
        # Always store in logfile if possible
        if logfileOutput is not None:
          logfileOutput.write( c.decode( 'utf-8', 'replace' ) )
          logfileOutput.flush()

        if capture:
          output.write( c )

        # Also duplicate output to stdout if requested
        if verbose:
          print( c.decode( 'utf-8', 'replace' ), flush=True, end="" )
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
    print( "\n", flush=True, end="" )

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

  def launch( self, working_directory ):
    # Immediately save the current state of this action
    self.save()

    # Self-submission of execute, but allowing more complex handling by re-entering into this script
    cmd = "./action_launcher.py"

    try:
      # Get extra submission stuff
      # if need to submit
      #   get submit cmd and args
      #   put Action.py cmd and config at the end
      if self._logfile is None and not self._verbose:
        self.log( "Action will not be printed to screen or saved to logfile" )
        self.log( "Consider modifying the action to use one of these two options" )
      retval, content = self.execute_subprocess(
                                                cmd,
                                                [ working_directory, self.save_file ],
                                                logfile=self._logfile,
                                                capture=True,
                                                verbose=self._verbose,
                                                dry_run=self._dry_run
                                                )

      # if need to submit
      #   get job id from content

      # Communicate up the chain
    except Exception as e:
      # Communicate up the chain that we failed :(

      # and propagate
      raise e

    return retval, content

  def setup( self ):
    # Setup action-specific stuff
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
    if environment is not None : self.environment = environment

    act_config = config.pop( "config", None )
    if act_config is not None : self.config = act_config

    self.add_dependencies( *config.pop( "dependencies", {} ).items() )
