import sane

@sane.register
def create_harvest_action( orch ):
  harvest = sane.Action( "harvest_action" )
  orch.add_action( harvest )

  harvest.config["command"]   = ".sane/mango/scripts/harvest.sh"

  harvest.environment = "valley"
  # no resource requirements listed for this action
  # set dependency to "grow_action" without having access
  # to the sane.Action( "grow_action" ) object itself
  harvest.add_dependencies( "grow_action" )
