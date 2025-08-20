import sane

@sane.register
def create_simple_host( orchestrator ):
  orchestrator.add_host( sane.Host( "unique_host_py" ) )
