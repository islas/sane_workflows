import unittest
import os
import sys

import sane


class MyAction( sane.Action ):
  def __init__( self, id, test_str, **kwargs ):
    self.test_str = test_str
    super().__init__( id, **kwargs )

  def run( self ):
    print( self.test_str )
    return 0


class ActionTests( unittest.TestCase ):
  def setUp( self ):
    self.action = sane.Action( "test" )
    self.action._verbose = True
    # Redirect logging to buffer
    # https://stackoverflow.com/a/7483862
    sane.console_handler.stream = sys.stdout

  def tearDown( self ):
    self.remove_save_files( self.action )

  def remove_save_files( self, state ):
    if os.path.isfile( state.save_file ):
      os.remove( state.save_file )

    if os.path.isfile( state.pickle_file ):
      os.remove( state.pickle_file )

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

    self.remove_save_files( host )

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

    self.remove_save_files( host )

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

    self.remove_save_files( host )

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

    self.remove_save_files( host )

  def test_action_external_definition( self ):
    """Test the ability to pickle an derived type action and relaunch it"""
    test_str = "MyAction will do as it pleases"

    self.action = MyAction( "test", test_str )
    self.action._verbose = True

    host = sane.Host( "basic" )
    host.add_environment( sane.Environment( "also_basic" ) )
    host.default_env = "also_basic"
    host.save()

    self.action.config["host_file"] = host.save_file

    retval, content = self.action.launch( os.getcwd() )
    self.assertEqual( retval, 0 )
    self.assertIn( test_str, content )

    self.remove_save_files( host )
