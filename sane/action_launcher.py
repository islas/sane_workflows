#!/usr/bin/env python3
import sys
import os
import pickle

import sane

if __name__ == "__main__":
  working_directory = sys.argv[1]
  action_file       = sys.argv[2]

  os.chdir( working_directory )

  action = sane.save_state.load( action_file )
  action.override_logname( f"{action.id}::launch" )
  action.log(  "*" * 15 + "{:^15}".format( "Inside action_launcher.py" ) + "*" * 15 )
  action.log( f"Loaded Action \"{action.id}\"" )

  if "host_file" not in action.config:
    raise Exception( "Missing host file!" )

  host = sane.save_state.load( action.config["host_file"] )

  action.log( f"Loaded Host \"{host.name}\"" )
  environment = host.has_environment( action.environment )
  if environment is None:
    raise Exception( f"Missing environment \"{action.environment}\"!" )

  action.log( f"Using Environment \"{environment.name}\"" )
  environment.setup()

  action.setup()
  retval = action.run()
  if retval is None:
    retval = -1
    action.log( f"No return value provided by Action {action.id}", level=40 )

  action.log(  "*" * 15 + "{:^15}".format( "Finished action_launcher.py" ) + "*" * 15 )

  exit( retval )
