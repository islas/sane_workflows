import sane


@sane.register
def my_workflow( orchestrator ):
  orchestrator.log( f"Hello world from {my_workflow.__name__}")


@sane.register( 1 )
def my_other_workflow( orchestrator ):
  orchestrator.log( "Creation of world" )


@sane.register( priority=5 )
def first_call( orchestrator ):
  orchestrator.log( "Creation of universe" )
