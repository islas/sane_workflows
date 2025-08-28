#!/usr/bin/env python3
import argparse
import os
import pathlib
import sys
import re
import logging


def get_parser():
  parser = argparse.ArgumentParser(
                                    description="Entry point for orchestrating actions"
                                    )

  parser.add_argument(
                      "-p", "--path",
                      action="append",
                      type=str,
                      default=[],
                      help="Path to search for workflows, if not specified default is ./. Use multiple times for many paths"
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
                      help="Search pattern used to find workflows, if not specified default is [*.json, *.jsonc, *.py], Use multiple times for many patterns"
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
                      "-n", "--new",
                      action="store_true",
                      default=None,
                      help="Start a new workflow run and clear previous cache"
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

  logfile = os.path.abspath( f"{options.log_location}/runner.log" )
  os.makedirs( os.path.dirname( logfile ), exist_ok=True )
  file_handler = logging.FileHandler( logfile, mode="w" )
  file_handler.setFormatter( sane.log_formatter )
  sane.internal_logger.addHandler( file_handler )
  logger.log( f"Logging output to {logfile}")

  if len( options.path ) == 0:
    options.path = [ "./" ]

  if len( options.search_pattern ) == 0:
    options.search_pattern = [ "*.json", "*.jsonc", "*.py" ]

  logger.log( "Searching for workflow files..." )
  files = []
  for search_path in options.path:
    for search_pattern in options.search_pattern:
      # Now search for each path each pattern
      logger.log( f"  Searching {search_path} for {search_pattern}" )
      for path in pathlib.Path( search_path ).rglob( search_pattern ):
        logger.log( f"    Found {path}" )
        files.append( path )

  files_sorted = {}
  for file in files:
    ext = file.suffix # os.path.splitext( file )
    if ext not in files_sorted:
      files_sorted[ext] = []

    files_sorted[ext].append( file )

  ##############################################################################
  orchestrator = sane.Orchestrator()

  # Do all python-based definitions first
  if ".py" in files_sorted:
    orchestrator.load_py_files( files_sorted[".py"] )

  orchestrator.process_registered()

  # Then finally do config files
  if ".json" in files_sorted:
    orchestrator.load_config_files( files_sorted[".json"] )

  if ".jsonc" in files_sorted:
    orchestrator.load_config_files( files_sorted[".jsonc"] )

  if options.verbose is not None:
    orchestrator.verbose = options.verbose

  orchestrator.save_location = options.save_location
  orchestrator.log_location = options.log_location
  orchestrator.working_dir = options.working_dir

  action_list = options.actions
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

  # Load any previous statefulness
  if not options.new:
    orchestrator.load()

  if options.run:
    orchestrator.run_actions( action_list, options.specific_host )
  if options.dry_run:
    orchestrator.dry_run = True
    orchestrator.run_actions( action_list, options.specific_host )
  elif options.list:
    logger.log( "Actions:" )
    sane.orchestrator.print_actions( action_list, print=logger.log )

  orchestrator.save()
  logger.log( "Finished" )


if __name__ == "__main__":
  main()
