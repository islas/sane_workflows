import unittest

import sane


class HPCHostTests( unittest.TestCase ):
  def setUp( self ):
    self.host = sane.PBSHost( "test" )

  def test_pbs_host_standalone( self ):
    """Ensure that a pbs host can be created standalone"""
    pass

  def test_pbs_host_from_config( self ):
    self.host.load_config(
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

  def test_pbs_host_resource_requisition( self ):
    self.test_pbs_host_from_config()
    _, submit_selection = self.host.pbs_resource_requisition( { "nodes" : 4, "cpus" : 256 }, "foo" )
    print( submit_selection )
    print( "Result: " + self.host._format_arguments( self.host.requisition_to_submit_args( submit_selection ) ) )


    _, submit_selection = self.host.pbs_resource_requisition( { "nodes" : 4, "cpus" : 256, "select" : "select=1:ncpus=8:ngpus=1" }, "foo" )
    print( submit_selection )
    print( "Result: " + self.host._format_arguments( self.host.requisition_to_submit_args( submit_selection ) ) )
