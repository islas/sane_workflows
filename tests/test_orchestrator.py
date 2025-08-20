import unittest
import os

import sane


class OrchestratorTests( unittest.TestCase ):
  def setUp( self ):
    self.orch = sane.Orchestrator()
    self.root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), ".." ) )

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

  def test_orchestrator_select_host( self ):
    """Test the ability to select host based on name or aliases"""
    self.orch.add_host( sane.Host( "dummy", aliases=["some_other_name"] ) )
    self.orch.hosts["dummy"].add_environment( sane.Environment( "generic" ) )
    self.orch.hosts["dummy"].default_env = "generic"

    self.orch.check_host( "dummy", { } )
    self.assertEqual( self.orch._current_host, "dummy" )

  def test_orchestrator_load_py( self ):
    """Test the ability to load py files"""
    self.orch.load_py_files( [ f"{self.root}/demo/simple_host.py"] )
    self.orch.process_registered()
    self.assertIn( "unique_host_py", self.orch.hosts )

  def test_orchestrator_load_config_host( self ):
    """Test the ability to load simple host from config files"""
    self.orch.load_config_files( [ f"{self.root}/demo/simple_host.jsonc"] )
    self.assertIn( "unique_host_config", self.orch.hosts )

  def test_orchestrator_load_config_action( self ):
    """Test the ability to load simple action from config files"""
    self.orch.load_config_files( [ f"{self.root}/demo/simple_action.json"] )
    self.assertIn( "unique_action_config", self.orch.actions )

  def test_orchestrator_fail_load_file_noexist( self ):
    """Test to make sure nonexistant files fail correctly when not found"""
    with self.assertRaises( FileNotFoundError ):
      self.orch.load_config_files( [ f"{self.root}/nosuchfile/in/this/project.json"] )
    with self.assertRaises( FileNotFoundError ):
      self.orch.load_py_files( [ f"{self.root}/nosuchfile/in/this/project.py"] )

