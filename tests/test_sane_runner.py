import unittest
import sys
import os
import io
import shutil
import json

import sane.sane_runner


class SaneRunnerTests( unittest.TestCase ):
  def setUp( self ):
    # Redirect logging to buffer
    # https://stackoverflow.com/a/7483862
    self.output = io.StringIO()
    sane.console_handler.stream = self.output
    self.root = os.path.abspath( os.path.join( os.path.dirname( __file__ ), ".." ) )

  def tearDown( self ):
    # https://stackoverflow.com/a/39606065
    if hasattr(self._outcome, 'errors'):
      # Python 3.4 - 3.10  (These two methods have no side effects)
      result = self.defaultTestResult()
      self._feedErrorsToResult(result, self._outcome.errors)
    else:
      # Python 3.11+
      result = self._outcome.result
    ok = all(test != self for test, text in result.errors + result.failures)
    if ok:
      shutil.rmtree( f"{self.root}/log" )

  def exit_ok( self, f ):
    with self.assertRaises( SystemExit ) as e:
      f()
    self.assertEqual( e.exception.code, 0 )

  def test_sane_runner_list_actions( self ):
    sys.argv = [ "foo", "-p", f"{self.root}/demo/", "-l" ]
    self.exit_ok( sane.sane_runner.main )

    output = self.output.getvalue()
    self.assertIn( "Listing actions:", output )

  def test_sane_runner_list_actions_filter( self ):
    sys.argv = [ "foo", "-p", f"{self.root}/demo/", "-l", "-f", "action_00[0-9]" ]
    self.exit_ok( sane.sane_runner.main )

    output = self.output.getvalue()
    self.assertIn( "Listing actions:", output )
    for i in range( 10 ):
      self.assertIn( f"action_{i:03d}", output )
    for i in range( 10, 20 ):
      self.assertNotIn( f"action_{i:03d}", output )

  def test_sane_runner_run_action_list( self ):
    sys.argv = [ "foo", "-p", f"{self.root}/demo/", "-n", "-r", "-a", "action_000", "action_001", "action_002" ]
    self.exit_ok( sane.sane_runner.main )

    output = self.output.getvalue()
    self.assertIn( "Running actions:", output )
    for i in range( 3 ):
      action = f"action_{i:03d}"
      self.assertIn( action, output )
      self.assertTrue( os.path.isfile( f"{self.root}/log/{action}.log") )

  def test_sane_runner_run_action_filter( self ):
    sys.argv = [ "foo", "-p", f"{self.root}/demo/", "-n", "-r", "-f", "action_00[0-9]" ]
    self.exit_ok( sane.sane_runner.main )

    output = self.output.getvalue()
    self.assertIn( "Running actions:", output )
    for i in range( 10 ):
      action = f"action_{i:03d}"
      self.assertIn( action, output )
      self.assertTrue( os.path.isfile( f"{self.root}/log/{action}.log") )

  def test_sane_runner_virtual_launch( self ):
    virtual_resources = { "cpus" : 12 }
    vdict = json.dumps( virtual_resources )
    sys.argv = [ "foo", "-p", f"{self.root}/demo/", "-n", "-r", "-f", "action_00[0-9]", "-vr", vdict ]
    self.exit_ok( sane.sane_runner.main )

    output = self.output.getvalue()
    self.assertIn( "Running actions:", output )
    for i in range( 3 ):
      # No action in main log, but the action log file should exist
      action = f"action_{i:03d}"
      self.assertNotIn( action, output )
      self.assertTrue( os.path.isfile( f"{self.root}/log/{action}.log") )


