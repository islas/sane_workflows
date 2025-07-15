#!/usr/bin/env python3
import json
import sys

from Action import Action

if __name__ == "__main__":
  config = None
  config_file = sys.argv[1]
  with open( config_file, "r" ) as f:
    config = json.load( f )

  id = config["id"]
  print( f"Spawning action {id}" )
  action = Action( id )
  action.set_config( config )

  action.setup()
  retval = action.run()
  if retval is None:
    retval = -1
    print( f"No return value provided by Action {id}" )
    
  exit( retval )
