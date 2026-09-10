import unittest
import subprocess
import os
import re
import sys

import sane


class MockHPC( sane.HPCHost ):
  def __init__( self, name, aliases=[] ):
    super().__init__(name, aliases)
    self.account = "foobar"
    self.runner_dir = os.path.dirname( __file__ ) + "/mock_hpc"
    self.runner = None
    self._state_cmd  = f"cat {self.runner_dir}/complete/{{0}}"
    self._status_cmd = self._state_cmd
    self._submit_cmd = f"{self.runner_dir}/submit.sh"
    self._delay_sec = 0.1
    self._cmd_delim = "--"
    self._submit_format["dependency"] = "{0}"

  def pre_run_actions( self, actions ):
    # Launch mock runner with 1 second delay
    self.runner = subprocess.Popen( [ self.runner_dir + "/run.sh", "0.1" ] )
    return super().pre_run_actions( actions )

  def post_run_actions( self, actions ):
    # Complete post run processing
    super().post_run_actions(actions)

    # Kill the mock runner
    with open( self.runner_dir + "/kill", "w" ):
      pass

    self.runner.wait()

  def check_job_complete( self, job_id, retval, status ):
    if retval != 0:
      return False

    return True

  def check_job_status( self, job_id, retval, status ):
    complete = self.check_job_complete( job_id, retval, status )
    if not complete:
      return False

    return int(status) == 0

  def extract_job_id( self, content ):
    found = re.match( r"^Launching job (\d+)", content )
    if found is None:
      self.log( "No job id found in output from job submission", level=40 )
      raise RuntimeError( "No job id found" )
    else:
      return int( found.group( 1 ) )

  def submit_args( self, resource_dict, requestor_name ):
    return {}, "none"

  # These are generally complex and I don't feel like writing them so just don't
  # over-subscribe your local system, ok?
  def nonlocal_acquire_resources( self, resource_dict, requestor ):
    return True

  def nonlocal_release_resources(self, resource_dict, requestor):
    return True

  def nonlocal_resources_available(self, resource_dict, requestor, log=True):
    return True


class HPCHostTests( unittest.TestCase ):
  def setUp( self ):
    self.host = sane.PBSHost( "test" )

    # Redirect logging to buffer
    # https://stackoverflow.com/a/7483862
    sane.logger.console_handler.stream = sys.stdout

  def tearDown( self ):
    self.remove_save_files( self.host )

  def remove_save_files( self, state ):
    if os.path.isfile( state.save_file ):
      os.remove( state.save_file )

    if os.path.isfile( state.pickle_file ):
      os.remove( state.pickle_file )

    if isinstance( state, sane.Action ):
      f = f"{state.save_location}/{state.id}_outputs.json"
      if os.path.isfile( f ):
        os.remove( f )
      f = state.runlog
      if f is not None and os.path.isfile( f ):
        os.remove( f )
      f = state.logfile
      if f is not None and os.path.isfile( f ):
        os.remove( f )

  def test_pbs_host_standalone( self ):
    """Ensure that a pbs host can be created standalone"""
    pass

  def test_pbs_host_from_options( self ):
    self.host.load_options(
      {
        "resources" :
        {
          "cpu" :
          {
            "nodes" : 2488,
            "exclusive" : True,
            "resources" : { "cpus" : 128, "memory" : "256gb" }
          },
          "gpu" :
          {
            "nodes" : 82,
            "resources" :
            { "cpus" : 64, "memory" : "512gb", "gpus:a100" : 4 }
          },
          "cpudev" :
          {
            "nodes" : 8,
            "exclusive" : False,
            "resources" :
            { "cpus" : 64, "memory" : "128gb" }
          }
        },
        "mapping" : { "ncpus" : ["cpus", "cpu"], "ngpus" : [ "gpus", "gpu" ] }
      }
    )
    self.assertIn( "cpu", self.host.resources )
    self.assertIn( "gpu", self.host.resources )
    self.assertIn( "cpudev", self.host.resources )
    self.assertIn( "node", self.host.resources["cpu"] )
    self.assertIn( "total", self.host.resources["cpu"] )
    self.assertIn( "exclusive", self.host.resources["cpu"] )
    self.assertIn( "ncpus", self.host.resources["cpu"]["total"].resources )
    self.assertIn( "memory", self.host.resources["cpu"]["total"].resources )
    self.assertIn( "ncpus", self.host.resources["gpu"]["total"].resources )
    self.assertIn( "ngpus:a100", self.host.resources["gpu"]["total"].resources )
    self.assertIn( "memory", self.host.resources["gpu"]["total"].resources )

    self.assertEqual( 82 * 64, self.host.resources["gpu"]["total"].resources["ncpus"].total )
    self.assertEqual( 82 * 4, self.host.resources["gpu"]["total"].resources["ngpus:a100"].total )
    self.assertEqual( 82 * 1024**3 * 512, self.host.resources["gpu"]["total"].resources["memory"].total )

  def test_pbs_host_resource_requisition( self ):
    dummy = sane.Action( "dummy" )
    self.test_pbs_host_from_options()
    _, submit_selection = self.host.pbs_resource_requisition( { "nodes" : 4, "cpus" : 256 }, dummy )
    submit_args, submit_queue = self.host.requisition_to_submit_args( submit_selection )
    result = self.host._format_arguments( submit_args )
    print( submit_selection )
    print( "Result: " + result )
    self.assertEqual( result, "-l select=4:ncpus=64" )
    self.assertEqual( submit_queue, None )

    _, submit_selection = self.host.pbs_resource_requisition(
      { "nodes" : 4, "cpus" : 256, "select" : "select=1:ncpus=8:ngpus=1" }, dummy
      )
    submit_args, submit_queue = self.host.requisition_to_submit_args( submit_selection )
    result = self.host._format_arguments( submit_args )
    print( submit_selection )
    print( "Result: " + result )
    # Note that the ngpus:a100 must be fixed somehow down the line
    self.assertEqual( result, "-l select=1:ncpus=8:ngpus:a100=1" )
    self.assertEqual( submit_queue, None )

  def test_pbs_host_resource_gen_wrapper( self ):
    self.test_pbs_host_from_options()
    action = sane.Action( "foo" )
    action.add_resource_requirements( { "nodes" : 4, "cpus" : 256, "queue" : "bar", "account" : "zoozar" } )
    available = self.host.resources_available( action.resources( "test" ), action )
    self.assertTrue( available )
    self.host.acquire_resources( { "nodes" : 4, "cpus" : 256 }, action )
    wrapper = self.host.launch_wrapper( action, {} )
    print( wrapper )

  def test_pbs_host_orch_integration( self ):
    self.test_pbs_host_from_options()
    orch = sane.Orchestrator()
    self.host.add_environment( sane.Environment( "generic" ) )
    orch.add_host( self.host )
    action = sane.Action( "my_action" )
    action.config["command"] = "echo"
    action.config["arguments"] = "foo bar zoo zar"
    action.environment = "generic"
    orch.add_action( action )
    orch.dry_run = True

    # Test that a queue and account must be provided in some manner
    with self.assertRaises( KeyError ):
      orch.run_actions( ["my_action"], as_host="test" )
    action.add_resource_requirements( { "test" : { "queue" : "queue_foo", "account" : "account_foo" } } )
    orch.run_actions( ["my_action"], as_host="test" )

    self.remove_save_files( action )
    os.remove( orch.save_file )
    os.remove( orch.results_file )

  def test_hpc_host_mock( self ):
    self.host = MockHPC( "mock_hpc" )
    orch = sane.Orchestrator()
    self.host.add_environment( sane.Environment( "generic" ) )

    orch.add_host( self.host )

    actionA = sane.Action( "my_actionA" )
    actionA.import_paths = [ os.path.dirname( __file__ ) ]
    actionA.config["command"] = "echo"
    actionA.config["arguments"] = ["foo bar zoo zar"]
    actionA.environment = "generic"

    actionB = sane.Action( "my_actionB" )
    actionB.import_paths = [ os.path.dirname( __file__ ) ]
    actionB.config["command"] = "echo"
    actionB.config["arguments"] = ["foo bar zoo zar"]
    actionB.environment = "generic"
    actionB.add_dependencies( actionA.id )

    orch.add_action( actionA )
    orch.add_action( actionB )
    orch.dry_run = False

    # Test that the action can be submitted
    orch.run_actions( ["my_actionB"], as_host="mock_hpc" )

    self.assertEqual( actionA.status, sane.ActionStatus.SUCCESS )
    self.assertEqual( actionA.state, sane.ActionState.FINISHED )

    self.assertEqual( actionB.status, sane.ActionStatus.SUCCESS )
    self.assertEqual( actionB.state, sane.ActionState.FINISHED )

    self.remove_save_files( actionA )
    self.remove_save_files( actionB )
    os.remove( orch.save_file )
    os.remove( orch.results_file )
