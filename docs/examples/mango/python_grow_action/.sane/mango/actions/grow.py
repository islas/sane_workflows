import sane

@sane.register
def create_grow_action( orch ):
  grow = sane.Action( "grow_action" )
  orch.add_action( grow )

  grow.config["command"]   = ".sane/mango/scripts/grow.sh"
  grow.config["arguments"] = [ 4 ] # this must be a list

  grow.environment = "valley"
  grow.add_resource_requirements( { "trees" : 4 } )
