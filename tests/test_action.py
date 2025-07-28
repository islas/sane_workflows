import unittest

import sane


class ActionTests( unittest.TestCase ):
  def setUp( self ):
    self.action = sane.Action( "test" )

  def test_action_standalone( self ):
    """Ensure that an action can be created standalone"""
    pass
