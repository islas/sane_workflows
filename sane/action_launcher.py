#!/usr/bin/env python3
import sys
import os


if __name__ == "__main__":
  filepath = os.path.dirname( os.path.abspath( __file__ ) )
  package_path = os.path.abspath( os.path.join( filepath, ".." ) )
  if package_path not in sys.path:
    sys.path.append( package_path )

  import sane

  working_directory = sys.argv[1]
  action_file       = sys.argv[2]
  sane.internal_logger.setLevel( sane.logger.STDOUT )

  action = sane.save_state.load( action_file )
  action.push_logscope( "launch" )
  action.log(  "*" * 15 + "{:^15}".format( "Inside action_launcher.py" ) + "*" * 15 )
  cwd = os.getcwd()
  action.log( f"Current directory: {cwd}")
  if cwd != working_directory:
    action.log( f"Changing directory to: {working_directory}")
    os.chdir( working_directory )

  action.log( f"Loaded Action \"{action.id}\"" )

  if "file" not in action.host_info:
    raise Exception( "Missing host file!" )

  host = sane.save_state.load( action.host_info["file"] )

  action.log( f"Loaded Host \"{host.name}\"" )
  environment = host.has_environment( action.environment )
  if environment is None:
    raise Exception( f"Missing environment \"{action.environment}\"!" )

  action.log( f"Using Environment \"{environment.name}\"" )
  environment.setup()

  if action.wrap_stdout:
    action.__exec_raw__ = False

  action.pre_run()
  retval = action.run()
  action.post_run( retval )

  if retval is None:
    retval = -1
    action.log( f"No return value provided by Action {action.id}", level=40 )

  action.log(  "*" * 15 + "{:^15}".format( "Finished action_launcher.py" ) + "*" * 15 )

  exit( retval )
