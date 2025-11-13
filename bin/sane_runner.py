#!/usr/bin/env python3
import argparse
import os
import sys
import re
import logging
import copy
import json


def get_parser():
  parser = argparse.ArgumentParser(
                                    description="Entry point for orchestrating actions"
                                    )

  parser.add_argument(
                      "-p", "--path",
                      action="append",
                      type=str,
                      default=[],
                      help="Path to search for workflows, default is ./. Use multiple times for many paths"
                      )
  parser.add_argument(
                      "-w", "--working_dir",
                      type=str,
                      default="./",
                      help="Location for actions to be run from, superseded by any action-specific working directory"
                      )
  parser.add_argument(
                      "-s", "--search_pattern",
                      action="append",
                      type=str,
                      default=[],
                      help="Search pattern used to find workflows, default is [*.json, *.jsonc, *.py], Use multiple times for many patterns"
                      )
  act_group = parser.add_argument_group( "Action Selection (choose only one)", "Select actions to operate on" )
  act_list = act_group.add_mutually_exclusive_group()
  act_list.add_argument(
                        "-a", "--actions",
                        nargs="+",
                        type=str,
                        default=[],
                        help="Actions in the workflow to run"
                        )
  act_list.add_argument(
                        "-f", "--filter",
                        type=str,
                        default=".*",
                        help="Select actions matching pattern, default '.*'"
                        )
  cmd_group = parser.add_argument_group( "Commands (choose only one)", "Set of commands operate on select actions" )
  cmd = cmd_group.add_mutually_exclusive_group()
  cmd.add_argument(
                    "-r", "--run",
                    action="store_true",
                    help="Run actions"
                    )
  cmd.add_argument(
                    "-l", "--list",
                    action="store_true",
                    help="List actions"
                    )
  cmd.add_argument(
                    "-d", "--dry-run",
                    action="store_true",
                    help="Run actions as dry-run"
                    )
  parser.add_argument(
                      "-sh", "--specific_host",
                      type=str,
                      default=None,
                      help="Run as a specific host"
                      )
  parser.add_argument(
                      "-sl", "--save_location",
                      type=str,
                      default="./tmp",
                      help="Location for saving intermediary pickling and JSON serialization of actions/hosts"
                      )
  parser.add_argument(
                      "-ll", "--log_location",
                      type=str,
                      default="./log",
                      help="Location for logfiles of stdout/stderr of workflow and actions"
                      )
  parser.add_argument(
                      "-v", "--verbose",
                      action="store_true",
                      default=None,
                      help="Verbose output from actions running"
                      )
  parser.add_argument(
                      "-g", "--debug_level",
                      action="store",
                      nargs="?",
                      default=20,
                      const=10,
                      type=int,
                      help="Log level of python logging levels"
                      )
  parser.add_argument(
                      "-vg", "--view_graph",
                      action="store_true",
                      default=None,
                      help="View CLI graph of actions"
                      )
  parser.add_argument(
                      "-fl", "--force_local",
                      action="store_true",
                      default=None,
                      help="Force local actions running of all actions"
                      )
  parser.add_argument(
                      "-n", "--new",
                      action="store_true",
                      default=None,
                      help="Start a new workflow run and clear previous cache"
                      )
  virtual_group = parser.add_argument_group(
                                            "Virtual Launch (in situ aggregation)",
                                            "Creates temporary action to facilitate adaptive running of workflow"
                                            )
  virtual_group.add_argument(
                            "-vr", "--virtual_relaunch",
                            type=str,
                            default=None,
                            help="Relaunch workflow with virtual copy of host with resource specifications"
                            )
  virtual_host = parser.add_argument_group(
                                            "Internal (DO NOT USE)",
                                            "Creates temporary host to facilitate adaptive running of workflow"
                                            )
  virtual_host.add_argument(
                            "-ml", "--main_log",
                            type=str,
                            default="runner.log",
                            help="Logfile name of sane_runner"
                            )
  virtual_host.add_argument(
                            "-vh", "--virtual_host",
                            type=str,
                            default=None,
                            help="Launch workflow with virtual copy of host with resource specifications, forced local"
                            )
  return parser


def main():
  filepath = os.path.dirname( os.path.abspath( __file__ ) )
  package_path = os.path.abspath( os.path.join( filepath, ".." ) )
  if package_path not in sys.path:
      sys.path.append( package_path )

  import sane

  logger = sane.logger.Logger( "sane_runner" )
  parser  = get_parser()
  options = parser.parse_args()
  sane.internal_logger.setLevel( options.debug_level )
  sys.excepthook = sane.log_exceptions

  logfile = os.path.abspath( f"{options.log_location}/{options.main_log}" )
  os.makedirs( os.path.dirname( logfile ), exist_ok=True )
  file_handler = logging.FileHandler( logfile, mode="w" )
  file_handler.setFormatter( sane.log_formatter )
  sane.internal_logger.addHandler( file_handler )
  logger.log( f"Logging output to {logfile}")

  if len( options.path ) == 0:
    options.path = [ "./" ]

  if len( options.search_pattern ) == 0:
    options.search_pattern = [ "*.json", "*.jsonc", "*.py" ]

  ##############################################################################
  orchestrator = sane.Orchestrator()
  orchestrator.add_search_paths( options.path )
  orchestrator.add_search_patterns( options.search_pattern )
  orchestrator.load_paths()

  action_list = options.actions.copy()

  if len( action_list ) == 0:
    # Use filter
    action_filter = re.compile( options.filter )
    for action in orchestrator.actions:
      if action_filter.match( action ):
        action_list.append( action )

  # Still nothing
  if len( action_list ) == 0:
    logger.log( "No actions selected" )
    parser.print_help()
    exit( 1 )
  else:
    orchestrator.check_action_id_list( action_list )

  if options.virtual_host is not None or options.virtual_relaunch is not None:
    # find specific host to use, copy it
    host_name = orchestrator.find_host( options.specific_host )
    host = copy.deepcopy( orchestrator.hosts[host_name] )
    host._name    = f"{host_name}-virtual"
    host.logname  = f"{host_name}-virtual"
    virtual_resources = options.virtual_relaunch if options.virtual_relaunch else options.virtual_host
    # override resources
    if isinstance( host, sane.resources.NonLocalProvider ):
      host.force_local = True
      host.local_resources.logname = f"{host.name}::local"
      host.local_resources.add_resources( json.loads( virtual_resources ), override=True )
    else:
      host.add_resources( json.loads( virtual_resources ), override=True )

    logger.log( f"Adding virtual host {host.name} to orchestrator" )
    orchestrator.add_host( host )

    if options.virtual_host:
      # Force usage of this virtual host
      logger.log( f"Removing old host {host_name}" )
      orchestrator.hosts.pop( host_name )
      options.force_local = True
      logger.log( f"Switching host to {host.name}" )
      options.specific_host = host.name
    else:
      # Test potential virtual host
      logger.log( "Force-checking virtual host ability to run all actions..." )
      tmp_host = orchestrator.hosts.pop( host_name )
      orchestrator.find_host( host.name )
      orchestrator.check_host( orchestrator.traversal_list( action_list ) )

      # Revert back
      orchestrator.hosts.pop( host.name )
      orchestrator.add_host( tmp_host )

      # in situ create an aggregate action
      relaunch_options = copy.deepcopy( options )
      relaunch_options.virtual_host = virtual_resources
      relaunch_options.virtual_relaunch = None
      relaunch_options.specific_host = host_name
      relaunch_options.main_log = "virtual_runner.log"
      opt_append = [ "path", "search_pattern" ]
      if relaunch_options.actions:
        del relaunch_options.filter
      else:
        del relaunch_options.actions

      optional_args = {}
      for key, value in vars( relaunch_options ).items():
        # Skip all false and None as we have those as defaults
        if value :
          if isinstance( value, list ) :
            optional_args[ key ] = value
          elif isinstance( value, bool ) :
            # As long as we are diligent about action=store_const (True) this will work
            optional_args[ key ] = None
          else :
            # Just as str
            optional_args[ key ] = str( value )

      args = []
      for key, value in optional_args.items() :
        args.append( f"--{key}" )
        if value:
          if isinstance( value, list ) :
            if key in opt_append:
              val_str = list( map( str, value ) )
              opt_key = args.pop()
              for vs in val_str:
                args.extend( [ opt_key, vs ] )
            else:
              args.extend( list( map( str, value ) ) )
          else :
            args.append( f"{value}" )
      action = sane.Action( "virtual_relaunch" )
      action.config["command"] = __file__
      action.config["arguments"] = args
      action.wrap_stdout = False
      action.add_resource_requirements( json.loads( virtual_resources ) )
      orchestrator.add_action( action )
      # Change action list to do this instead
      action_list = [ "virtual_relaunch" ]

  if options.verbose is not None:
    logger.log( "Changing all actions output to verbose" )
    orchestrator.verbose = options.verbose

  if options.force_local is not None:
    logger.log( "Forcing all actions to run local" )
    orchestrator.force_local = options.force_local

  orchestrator.save_location = options.save_location
  orchestrator.log_location = options.log_location
  orchestrator.working_directory = options.working_dir

  # Load any previous statefulness
  if not options.new:
    orchestrator.load()

  orchestrator.setup()
  success = True
  orchestrator.dry_run = options.dry_run

  if options.run:
    success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )
  elif options.dry_run:
    success = orchestrator.run_actions( action_list, options.specific_host, visualize=options.view_graph )
  elif options.list:
    logger.log( "Listing actions:" )
    orchestrator.construct_dag()
    orchestrator.print_actions( action_list, options.view_graph )

  logger.log( "Finished" )
  file_handler.flush()
  file_handler.close()
  # Flip success as 1 == True and 0 == False
  # but exit codes 0 == ok anything else not ok
  exit( not int(success) )


if __name__ == "__main__":
  main()
