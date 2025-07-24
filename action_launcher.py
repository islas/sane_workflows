#!/usr/bin/env python3
import sys
import os
import pickle

from Action import Action

if __name__ == "__main__":
  working_directory = sys.argv[1]
  action_file       = sys.argv[2]

  os.chdir( working_directory )

  action = None
  with open( action_file, "rb" ) as f:
    action = pickle.load( f )

  print( f"Loaded Action \"{action.id_}\"" )

  host = None
  with open( action.config_["host_file"], "rb" ) as f:
    host = pickle.load( f )
  
  print( f"Loaded Host \"{host.name_}\"" )

  action.setup()
  retval = action.run()
  if retval is None:
    retval = -1
    print( f"No return value provided by Action {id}" )
    
  exit( retval )
