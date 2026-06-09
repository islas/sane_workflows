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
    self.action.verbose = True
    # Redirect logging to buffer
    # https://stackoverflow.com/a/7483862
    sane.logger.console_handler.stream = sys.stdout

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

    self.action.__host_info__["file"] = host.save_file

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
    self.action.__host_info__["file"] = host.save_file

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

    self.action.__host_info__["file"] = host.save_file
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

    self.action.__host_info__["file"] = host.save_file

    retval, content = self.action.launch( os.getcwd() )
    self.assertEqual( retval, 1 )
    self.assertIn( "No command provided for default Action", content )

    self.remove_save_files( host )

  def test_action_external_definition( self ):
    """Test the ability to pickle an derived type action and relaunch it"""
    test_str = "MyAction will do as it pleases"

    self.action = MyAction( "test", test_str )
    self.action.verbose = True

    host = sane.Host( "basic" )
    host.add_environment( sane.Environment( "also_basic" ) )
    host.default_env = "also_basic"
    host.save()

    self.action.__host_info__["file"] = host.save_file
    self.action.import_paths = [ os.path.dirname( __file__ ) ]
    retval, content = self.action.launch( os.getcwd() )
    self.assertEqual( retval, 0 )
    self.assertIn( test_str, content )

    self.remove_save_files( host )

  def test_action_from_options( self ):
    """Test setting up an action from a options dict"""
    options = {
                "environment" : "foobar",
                "local"       : True,
                "config"      :
                { 
                  "one" : 1,
                  "two" : [2],
                  "three" : { "foo" : 3 },
                  "foobar" : "foo",
                  "arr" : [ 3, 2, 1, 0 ]
                },
                "dependencies" :
                {
                  "dep_action0" : "afterok",
                  "dep_action1" : sane.action.DependencyType.AFTERNOTOK,
                  "dep_action2" : "afterany",
                  "dep_action3" : sane.action.DependencyType.AFTER,
                },
                "resources" :
                {
                  "cpus" : 1,
                  "gpus" : 999,
                  "memory" : "1234gb",
                  "gpus:a100" : 9999,
                  "timelimit"   : "12:34:56",
                  "host" :
                  {
                    "cpus" : 20,
                    "account" : "foo",
                    "queue" : "bar",
                    "select" : "select=2:mpiprocs4:ncpus:128+3:ncpus=4"
                  }
                }
              }
    self.action.load_options( options )
    self.assertEqual( options, {} )
    self.assertIn( "dep_action0", self.action.dependencies )
    self.assertIn( "dep_action1", self.action.dependencies )
    self.assertIn( "dep_action2", self.action.dependencies )
    self.assertIn( "dep_action3", self.action.dependencies )
    self.assertEqual( self.action.dependencies["dep_action0"]["dep_type"], sane.action.DependencyType.AFTEROK )
    self.assertEqual( self.action.dependencies["dep_action1"]["dep_type"], sane.action.DependencyType.AFTERNOTOK )
    self.assertEqual( self.action.dependencies["dep_action2"]["dep_type"], sane.action.DependencyType.AFTERANY )
    self.assertEqual( self.action.dependencies["dep_action3"]["dep_type"], sane.action.DependencyType.AFTER )
    self.assertEqual( self.action.environment, "foobar" )

  def test_action_dereference( self ):
    """Test the action's ability to use YAML-like attribute dereferencing"""
    # Start with a sufficiently complex config
    self.test_action_from_options()
    ref_str = "foo ${{ id }} ${{ environment}} ${{ local }} ${{ working_directory }}"
    exp_str = "foo test foobar True ./"
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

    ref_dict = {
                "foo" : "${{ id }}",
                "foobar" : ["${{environment}}"],
                "zoo" :
                {
                  "foo" : "${{ local }}",
                  "foobar" : "${noop}",
                  "noop" : "${{ }}",
                  "moo" : [ "${{ working_directory}}", "${{ config.one }}", "${{ resources.gpus}}" ]
                },
                "boo" : "${{ config.two[0] }}",
                "moo" : "${{ config.two[ ${{ config.arr[ ${{ config.three.${{ config.foobar }} }} ] }} ] }}"
              }
    exp_dict = {
                "foo" : "test",
                "foobar" : ["foobar"],
                "zoo" :
                {
                  "foo" : "True",
                  "foobar" : "${noop}",
                  "noop" : "${{ }}",
                  "moo" : [ "./", "1", "999" ]
                },
                "boo" : "2",
                "moo" : "2"
              }
    out_dict = self.action.dereference( ref_dict )
    self.assertEqual( exp_dict, out_dict )

    # multi-dereference
    self.action.config["foo"] = "${{ config.bar }}"
    self.action.config["bar"] = "1"
    ref_str = "${{config.foo}}"
    exp_str = "1"
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

  def test_action_dereference_detect_cycle( self ):
    """Test the action's ability to detect cycles in attribute dereferencing"""
    # Start with a sufficiently complex config
    self.test_action_from_options()

    # Modify action to self reference
    self.action.config["single_cycle"] = {
                                          "a" : "${{ config.single_cycle.b }}",
                                          "b" : "${{ config.single_cycle.a }}"
                                          }

    ref_str = "${{ config.single_cycle.a }}"
    exp_str = ref_str
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

    self.action.config["quad_cycle"] = {
                                          "a" : "${{ config.quad_cycle.b }}",
                                          "b" : "${{ config.quad_cycle.c }}",
                                          "c" : "${{ config.quad_cycle.d }}",
                                          "d" : "${{ config.quad_cycle.a }}"
                                          }

    ref_str = "${{ config.quad_cycle.a }}"
    exp_str = ref_str
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

    self.action.config["enter_cycle"] = {
                                          "a" : "${{ config.enter_cycle.b }}",
                                          "b" : "${{ config.enter_cycle.c }}",
                                          "c" : "${{ config.enter_cycle.d }}",
                                          "d" : "${{ config.quad_cycle.b }}"
                                        }
    # Enter cycle at b, so expect b out
    ref_str = "${{ config.enter_cycle.a }}"
    exp_str = self.action.config["enter_cycle"]["d"]
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

    # Cycle starts but does one loop to regularize the string so first err will
    # be at next node
    ref_str = "${{   config.single_cycle.a   }}"
    exp_str = self.action.config["single_cycle"]["a"] #goes to next node
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )

  def test_action_dereference_warn_simplified_re( self ):
    """Test the action's ability to detect malformed reference due to simplified regex"""
    # Start with a sufficiently complex config
    self.test_action_from_options()

    # The simplification of the regex to be a repeating pattern with an optional
    # '.' (key subscript) at the end allows a ref string to end with a '.'
    self.action.config["foo"] = 1

    # Detect if this is caught
    ref_str = "${{config.foo.}}"
    exp_str = "1"
    out_str = self.action.dereference_str( ref_str )
    self.assertEqual( exp_str, out_str )
