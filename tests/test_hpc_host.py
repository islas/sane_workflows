import unittest

import sane
from sane.helpers import recursive_update

class HPCHostTests( unittest.TestCase ):
  def setUp( self ):
    self.host = sane.PBSHost( "test" )

  def test_pbs_host_standalone( self ):
    """Ensure that a pbs host can be created standalone"""
    pass

  def test_pbs_host_from_options( self ):
    self.host.load_options(
      {
        "resources" :
        {
          "cpu" :
          {
            "nodes" : 2488,
            "exclusive" : True,
            "resources" : { "cpus" : 128, "memory" : "256gb" }
          },
          "gpu" :
          {
            "nodes" : 82,
            "resources" :
            { "cpus" : 64, "memory" : "512gb", "gpus:a100" : 4 }
          },
          "cpudev" :
          {
            "nodes" : 8,
            "exclusive" : False,
            "resources" :
            { "cpus" : 64, "memory" : "128gb" }
          }
        },
        "mapping" : { "ncpus" : ["cpus", "cpu"], "ngpus" : [ "gpus", "gpu" ] }
      }
    )
    self.assertIn( "cpu", self.host.resources )
    self.assertIn( "gpu", self.host.resources )
    self.assertIn( "cpudev", self.host.resources )
    self.assertIn( "node", self.host.resources["cpu"] )
    self.assertIn( "total", self.host.resources["cpu"] )
    self.assertIn( "exclusive", self.host.resources["cpu"] )
    self.assertIn( "ncpus", self.host.resources["cpu"]["total"].resources )
    self.assertIn( "memory", self.host.resources["cpu"]["total"].resources )
    self.assertIn( "ncpus", self.host.resources["gpu"]["total"].resources )
    self.assertIn( "ngpus:a100", self.host.resources["gpu"]["total"].resources )
    self.assertIn( "memory", self.host.resources["gpu"]["total"].resources )

    self.assertEqual( 82 * 64, self.host.resources["gpu"]["total"].resources["ncpus"].total )
    self.assertEqual( 82 * 4,  self.host.resources["gpu"]["total"].resources["ngpus:a100"].total )
    self.assertEqual( 82 * 1024**3 * 512, self.host.resources["gpu"]["total"].resources["memory"].total )


  def test_pbs_host_resource_requisition( self ):
    dummy = sane.Action( "dummy" )
    self.test_pbs_host_from_options()
    _, submit_selection = self.host.pbs_resource_requisition( { "nodes" : 4, "cpus" : 256 }, dummy )
    result = self.host._format_arguments( self.host.requisition_to_submit_args( submit_selection ) )
    print( submit_selection )
    print( "Result: " + result )
    self.assertEqual( result, "-l select=4:ncpus=64" )


    _, submit_selection = self.host.pbs_resource_requisition( { "nodes" : 4, "cpus" : 256, "select" : "select=1:ncpus=8:ngpus=1" }, dummy )
    result = self.host._format_arguments( self.host.requisition_to_submit_args( submit_selection ) )
    print( submit_selection )
    print( "Result: " + result )
    # Note that the ngpus:a100 must be fixed somehow down the line
    self.assertEqual( result, "-l select=1:ncpus=8:ngpus:a100=1" )


  def test_pbs_host_resource_gen_wrapper( self ):
    self.test_pbs_host_from_options()
    action = sane.Action( "foo" )
    action.add_resource_requirements( { "nodes" : 4, "cpus" : 256, "queue" : "bar", "account" : "zoozar" } )
    available = self.host.resources_available( action.resources( "test" ), action )
    self.assertTrue( available )
    self.host.acquire_resources( { "nodes" : 4, "cpus" : 256 }, action )
    wrapper = self.host.launch_wrapper( action, {} )
    print( wrapper )

  def test_pbs_host_orch_integration( self ):
    self.test_pbs_host_from_options()
    orch = sane.Orchestrator()
    self.host.add_environment( sane.Environment( "generic" ) )
    orch.add_host( self.host )
    action = sane.Action( "my_action" )
    action.config["command"] = "echo"
    action.config["arguments"] = "foo bar zoo zar"
    action.environment = "generic"
    orch.add_action( action )
    orch.dry_run = True

    with self.assertRaises( KeyError ):
      orch.run_actions( ["my_action"], as_host="test" )
    action.add_resource_requirements( { "test" : { "queue" : "queue_foo", "account" : "account_foo" } } )
    orch.run_actions( ["my_action"], as_host="test" )
