import sane


@sane.register( priority=10 )
def actual_workflow_hosts( orchestrator ):
  # Create a generic host that always matches with alias "."
  host = sane.Host( "generic", aliases=[ "." ] )
  host.add_resources( { "cpus" : 12, "memory" : "2gb" } )

  # Similarly create a generic environment
  env = sane.Environment( "generic" )

  host.add_environment( env )
  host.default_env = env.name

  orchestrator.add_host( host )


@sane.register
def actual_workflow_actions( orchestrator ):
  n_start = 15
  curr_id = 0

  layers = {}
  for layer in range( n_start ):
    layers[layer] = []
    for i in range( n_start - layer ):
      action_name = f"action_{curr_id:03d}"
      curr_id += 1

      action = sane.Action( action_name )
      action.config["command"] = "echo"
      action.config["arguments"] = [ action_name ]
      action._verbose = True
      if layer > 0:
        action.add_dependencies( *layers[layer - 1][i:i + 2] )
        action.config["arguments"].append( "depends on => " )
        action.config["arguments"].append( str( list( action.dependencies.keys() ) ) )

      layers[layer].append( action_name )
      orchestrator.add_action( action )
