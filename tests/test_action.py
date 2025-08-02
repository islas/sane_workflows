import unittest
import os

import sane


class ActionTests( unittest.TestCase ):
  def setUp( self ):
    self.action = sane.Action( "test" )
    self.action._verbose = True

  def tearDown( self ):
    self.remove_save_file( self.action )

  def remove_save_file( self, state ):
    if os.path.isfile( state.save_file ):
      os.remove( state.save_file )

  def test_action_standalone( self ):
    """Ensure that an action can be created standalone"""
    pass

  def test_action_launch_failure_no_host( self ):
    """Test that without a host object launching will fail"""
    retval, content = self.action.launch( os.getcwd() )
    self.assertNotEqual( retval, 0 )
    self.assertIn( "Missing host file", content )

  def test_action_launch_failure_no_default_env( self ):
    """Test that without no environment settings object launching will fail"""
    host = sane.Host( "basic" )
    host.save()
    self.action.config["host_file"] = host.save_file

    retval, content = self.action.launch( os.getcwd() )
    self.assertNotEqual( retval, 0 )
    self.assertIn( "Missing environment", content )

    self.remove_save_file( host )

  def test_action_launch_failure_no_env( self ):
    """Test that without proper environment object launching will fail"""
    self.action.environment = "not_basic"

    host = sane.Host( "basic" )
    host.add_environment( sane.Environment( "also_basic" ) )
    host.save()
    self.action.config["host_file"] = host.save_file

    retval, content = self.action.launch( os.getcwd() )
    self.assertNotEqual( retval, 0 )
    self.assertIn( "Missing environment", content )

    self.remove_save_file( host )

  def test_action_launch_success_default_env( self ):
    """Test that without action environment object launching will succeed if host has default"""
    host = sane.Host( "basic" )
    host.add_environment( sane.Environment( "also_basic" ) )
    host.default_env = "also_basic"
    host.save()

    self.action.config["host_file"] = host.save_file
    self.action.config["command"]   = "echo"
    self.action.config["arguments"] = ["this is an argument"]

    retval, content = self.action.launch( os.getcwd() )
    self.assertEqual( retval, 0 )
    self.assertIn( "this is an argument", content )

    self.remove_save_file( host )

  def test_action_launch_success_default_env( self ):
    """Test that without a command the default action, host and environment will fail"""
    host = sane.Host( "basic" )
    host.add_environment( sane.Environment( "also_basic" ) )
    host.default_env = "also_basic"
    host.save()

    self.action.config["host_file"] = host.save_file

    retval, content = self.action.launch( os.getcwd() )
    self.assertEqual( retval, 1 )
    self.assertIn( "No command provided for default Action", content )

    self.remove_save_file( host )
