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

  print( f"Loaded Action \"{action.id}\"" )

  if "host_file" not in action.config:
    raise Exception( "Missing host file!" )

  host = sane.save_state.load( action.config["host_file"] )

  print( f"Loaded Host \"{host.name}\"" )
  environment = host.has_environment( action.environment )
  if environment is None:
    raise Exception( f"Missing environment \"{action.environment}\"!" )

  print( f"Using Environment \"{environment.name}\"" )
  environment.setup()

  action.setup()
  retval = action.run()
  if retval is None:
    retval = -1
    print( f"No return value provided by Action {id}" )

  exit( retval )
