from Orchestrator import register
from Action import Action

@register
def my_tests( orchestrator ):
  print( "foo" )
  z = Action( "z" )
  z.set_config(
    {
      "command"   : "echo",
      "arguments" : z.id_
    }
  )
  z.add_dependencies( "h", "b" )
  orchestrator.add_action( z )
  orchestrator.actions_["l"].add_dependencies( "z" )
