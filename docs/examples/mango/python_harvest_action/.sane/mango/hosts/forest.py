import sane

@sane.register
def create_forest_host( orch ):
  forest = sane.Host( "forest" )
  orch.add_host( forest )

  forest.add_resources( { "trees" : 12 } )

  valley = sane.Environment( "valley" )
  river = sane.Environment( "river" )

  valley.setup_env_vars( "set", "GROWTH_RATE", 85 )
  river.setup_env_vars( "set", "GROWTH_RATE", 65 )

  forest.add_environment( valley )
  forest.add_environment( river )


