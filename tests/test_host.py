import unittest

import sane


class HostTests( unittest.TestCase ):
  def setUp( self ):
    self.host = sane.Host( "test" )

  def test_host_standalone( self ):
    """Ensure that a host can be created standalone"""
    pass
