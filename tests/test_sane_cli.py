import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from sane import sane_runner, sane_view
from sane import sane as sane_cli


class SaneCliTests( unittest.TestCase ):
  def test_shared_options( self ):
    cases = [
      ( "workflow", sane_runner, [ "-p", "demo", "-a", "action_000", "-d", "-vr", '{"cpus": 2}' ] ),
      ( "view", sane_view, [ "logs", "saved", "-e", "-rp", "-md" ] ),
      ( "view", sane_view, [ "usage", "-a", "-s" ] ),
      ( "view", sane_view, [ "status", "-l", "80" ] ),
      ( "view", sane_view, [ "state" ] ),
      ( "view", sane_view, [ "summary", "-md" ] ),
    ]
    for command, module, args in cases:
      with self.subTest( command=command, args=args ):
        options = sane_cli.get_parser().parse_args( [ command ] + args )
        del options.command
        vars( options ).pop( "_parser", None )
        self.assertEqual( vars( options ), vars( module.get_parser().parse_args( args ) ) )

  def test_dispatch_removes_routing_options( self ):
    for command, module, args in [
      ( "workflow", sane_runner, [ "-p", "demo", "-l" ] ),
      ( "view", sane_view, [ "logs" ] ),
    ]:
      with patch.object( sys, "argv", [ "sane", command ] + args ), patch.object( module, "main" ) as main:
        sane_cli.main()
        options = main.call_args[0][0]
        self.assertEqual( vars( options ).pop( "_parser" ).prog, "sane " + command )
        self.assertEqual( main.call_args[1], {} )
        self.assertEqual( vars( options ), vars( module.get_parser().parse_args( args ) ) )

  def test_view_consumes_parser_metadata( self ):
    for cmd, handler in [
      ( "usage", "plot_usage" ),
      ( "status", "show_status" ),
      ( "state", "show_state" ),
      ( "logs", "show_logs" ),
      ( "summary", "show_summary" ),
    ]:
      with self.subTest( cmd=cmd ):
        options = sane_cli.get_parser().parse_args( [ "view", cmd ] )
        del options.command
        self.assertTrue( hasattr( options, "_parser" ) )
        with patch.object( sane_view, handler ) as show, patch.object( sane_view, "get_parser" ) as get_parser:
          sane_view.main( options )
          get_parser.assert_not_called()
          show.assert_called_once_with( "./tmp/orchestrator.json", options )
        self.assertFalse( hasattr( options, "_parser" ) )

  def test_subcommands_required( self ):
    for args in [ [], [ "view" ] ]:
      with contextlib.redirect_stderr( io.StringIO() ), self.assertRaises( SystemExit ) as error:
        sane_cli.get_parser().parse_args( args )
      self.assertEqual( error.exception.code, 2 )

  def test_direct_scripts( self ):
    root = Path( __file__ ).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
      saved = Path( tmp ) / "orchestrator.json"
      saved.write_text( json.dumps( {
        "actions": { "example": { "status": "success", "logfile": "/tmp/example.log" } }
      } ) )
      for script, args in [
        ( "sane", [ "view", "logs", tmp ] ),
        ( "sane_view", [ "logs", tmp ] ),
        ( "sane_runner", [ "--help" ] ),
        ( "sane", [ "workflow", "--help" ] ),
      ]:
        with self.subTest( script=script, args=args ):
          result = subprocess.run(
                                  [ str( root / "bin" / (script + ".py") ) ] + args,
                                  cwd=tmp,
                                  env=dict( os.environ, PYTHONPATH=str( root ) ),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True
                                  )
          self.assertEqual( result.returncode, 0, result.stderr )
          if "logs" in args:
            self.assertIn( "/tmp/example.log", result.stdout )
          self.assertEqual( "deprecated" in result.stderr, script != "sane" )

  def test_workflow_virtual_relaunch( self ):
    root = Path( __file__ ).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
      result = subprocess.run(
                              [
                                str( root / "bin" / "sane.py" ), "workflow", "-p", str( root / "demo" ),
                                "-r", "-a", "action_000", "-vr", '{"cpus": 12}'
                              ],
                              cwd=tmp,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True,
                              timeout=60
                              )
      self.assertEqual( result.returncode, 0, result.stdout + result.stderr )
      self.assertTrue( ( Path( tmp ) / "log" / "action_000.log" ).is_file() )
      relaunch_log = ( Path( tmp ) / "log" / "virtual_relaunch.log" ).read_text()
      self.assertIn( "sane.py workflow", relaunch_log )
      self.assertNotIn( "deprecated", relaunch_log )

  def test_no_actions_help_uses_active_entry_point( self ):
    root = Path( __file__ ).resolve().parents[1]
    for script, prefix in [ ( "sane", [ "workflow" ] ), ( "sane_runner", [] ) ]:
      with self.subTest( script=script ), tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
                                [ str( root / "bin" / (script + ".py") ) ] + prefix
                                + [ "-p", str( root / "demo" ), "-f", "^no_matching_actions$", "-l" ],
                                cwd=tmp,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True
                                )
        self.assertEqual( result.returncode, 1, result.stdout + result.stderr )
        invocation = " ".join( [ script + ".py" ] + prefix )
        self.assertIn( "usage: " + invocation + " ", result.stdout )
        self.assertIn( "--path", result.stdout )

  def test_help_defers_plotting_imports( self ):
    root = Path( __file__ ).resolve().parents[1]
    code = '''
import sys
from sane import sane as sane_cli
sane_cli.get_parser().parse_args( [ "view", "usage" ] )
assert "matplotlib" not in sys.modules
'''
    result = subprocess.run(
                            [ sys.executable, "-c", code ],
                            cwd=str( root ),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True
                            )
    self.assertEqual( result.returncode, 0, result.stderr )
