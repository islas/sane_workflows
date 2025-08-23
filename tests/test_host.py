import unittest

import sane


class HostTests( unittest.TestCase ):
  def setUp( self ):
    self.host = sane.Host( "test" )

  def test_host_standalone( self ):
    """Ensure that a host can be created standalone"""
    pass

  def test_pbs_host_standalone( self ):
    self.host = sane.PBSHost( "test" )
    submit_selection = self.host.acquire_resource_from_nodes( { "nodes" : 4, "cpus" : 256 } )
    print( submit_selection )
    print( "Result: " + self.host._format_arguments( submit_selection ) )


    submit_selection = self.host.acquire_resource_from_nodes( { "nodes" : 4, "cpus" : 256, "select" : "select=1:ncpus=8:ngpus=1" } )
    print( submit_selection )
    print( "Result: " + self.host._format_arguments( submit_selection ) )