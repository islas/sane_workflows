import os
import json
import shutil
import sys
import io
import subprocess
from enum import Enum

from Logger import *

class DependencyType( str, Enum ):
  AFTEROK    = "afterok"    # after successful run (this is the default)
  AFTERNOTOK = "afternotok" # after failure
  AFTERANY   = "afterany"   # after either failure or success
  AFTER      = "after"      # after the step *starts*
  def __str__( self ) :
    return str( self.value )
  def __repr__( self ) :
    return str( self.value )

class ActionState( Enum ):
  PENDING  = 0
  RUNNING  = 1
  FINISHED = 2
  INACTIVE = 3
  ERROR    = 4 # This should not be used for errors in running the action (status),
               # Instead this should be reserved for internal errors of the action


class Action( Logger ):
  def __init__( self, id ):
    self.id_ = id
    self.config_ = {}

    self.verbose_ = False
    self.dryRun_  = False

    self.logfile_          = None
    self.state_            = ActionState.INACTIVE
    self.dependencies_     = {}

    super().__init__( id )


  def set_config( self, config ):
    self.config_ = config
  
  def set_config_from_file( self, config_file ):
    with open( config_file, "r" ) as f:
      self.config_ = json.load( f )

  def add_dependencies( self, *args ):
    arg_idx = -1
    for arg in args:
      arg_idx += 1
      if isinstance( arg, str ):
        self.dependencies_[arg] = DependencyType.AFTEROK
      elif isinstance( arg, tuple ) and len(arg) == 2 and isinstance( arg[0], str ) and arg[1] in DependencyType :
        self.dependencies_[arg[0]] = DependencyType[arg[1]]
      else:
        msg = f"Error: Argument {arg_idx} is invalid for {Action.add_dependencies.__name__}(), must be of type str or tuple( str, DependencyType.value->str )"
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
    self.log(  "*" * 15 + "{:^15}".format( "START " + self.id_ ) + "*" * 15 + "\n" )

    retval  = -1
    content = None

    if not dry_run :
      ############################################################################
      ##
      ## Call subprocess
      ##
      # https://stackoverflow.com/a/18422264
      if logfile is not None and verbose:
        self.log( "Local step will also be captured to logfile {0}".format( logfile ) )

      # Keep a duplicate of the output as well in memory as a string
      output = None
      if capture :
        output = io.BytesIO()

      proc = subprocess.Popen(
                              args,
                              stdin =subprocess.PIPE,
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
        if verbose :
          sys.stdout.buffer.write(c)
          sys.stdout.flush()

      # We don't mind doing this as the process should block us until we are ready to continue
      dump, err    = proc.communicate()
      retval       = proc.returncode
      ##
      ## 
      ##
      ############################################################################
    else :
      self.log( "Doing dry-run, no ouptut" )
      retval = 0
      output = "12345"

    # self.log( "\n" )
    print( "\n", flush=True, end="" )

    self.log(  "*" * 15 + "{:^15}".format( "STOP " + self.id_ ) + "*" * 15 )

    if not dry_run :
      if capture :
        if False: # TODO Not sure which conditional is supposed to lead here
          output.seek(0)
          content = output.read()
        else : 
          content = output.getvalue().decode( 'utf-8' )
        output.close()
    else :
      content = output

    return retval, content

  def launch( self ):
    # Self-submission of execute, but allowing more complex handling by re-entering into this script
    cmd = "./action_launcher.sh"
    config = self.config_.copy()
    if not "submit_options" in config:
      config["submit_options"] = {}

    config["submit_options"]["submit_type"] = "LOCAL"
    config["id"] = self.id_

    tmp_file = f"./{self.id_}_config.json"
    with open( tmp_file, "w" ) as f:
      json.dump( config, f, indent=2 )
    
    try:
      # Get extra submission stuff
      # if need to submit
      #   get submit cmd and args
      #   put Action.py cmd and config at the end
      if self.logfile_ is None and not self.verbose_:
        self.log( "Action will not be printed to screen or saved to logfile" )
        self.log( "Consider modifying the action to use one of these two options" )
      retval, content = self.execute_subprocess( cmd, [ os.getcwd(), tmp_file ], logfile=self.logfile_, capture=True, verbose=self.verbose_, dry_run=self.dryRun_ )

      # if need to submit
      #   get job id from content
    
      # Communicate up the chain
    except Exception as e:
      # Communicate up the chain that we failed :(
      
      # and propagate
      raise e

  def setup( self ):
    # Setup environment stuff
    self.log( "Setting up environment" )
  

  def run( self ):
    # Users may overwrite run() in a derived class, but a default will be provided for config-file based testing (TBD)
    # The default will simply launch an underlying command using a subprocess
    command = None
    if "command" in self.config_:
      command = self.config_["command"]
    
    if command is None:
      self.log( "No command provided for default Action" )
      exit( 1 )
    
    arguments = None
    if "arguments" in self.config_:
      arguments = self.config_["arguments"]

    retval, content = self.execute_subprocess( command, arguments, verbose=True )
    return retval
    
  def __repr__( self ):
    return f"Action({self.id_})"

