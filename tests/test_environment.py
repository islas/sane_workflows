import unittest

import sane

class EnvironmentTests( unittest.TestCase ):
  def setUp( self ):
    self.environment = sane.Environment( "test" )
  
  def test_environment_standalone( self ):
    """Ensure that an environment can be created standalone"""
    pass
