import unittest

import sane


class OrchestratorTests( unittest.TestCase ):
  def setUp( self ):
    self.orch = sane.Orchestrator()

  def test_orchestrator_standalone( self ):
    """Ensure that an environment can be created standalone"""
    pass

  def test_orchestrator_external_register( self ):
    """Test the ability to register external functions"""
    x = None

    @sane.register
    def external_function( orchestrator ):
      orchestrator.add_host( sane.Host( "dummy" ) )

    self.orch.process_registered()
    self.assertIn( "dummy", self.orch.hosts )

  # def test_orchestrator_select_host( self ):
  #   """Test the ability to select host based on name or aliases"""
  #   self.orch.add_host( sane.Host( "dummy" ) )

  #   self.orch.
