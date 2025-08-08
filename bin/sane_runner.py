#!/usr/bin/env python3
import argparse
import os
import pathlib
import sys

import sane


def get_parser():
  parser = argparse.ArgumentParser(
                                    description="Entry point for orchestrating actions"
                                    )

  parser.add_argument(
                      "-p", "--path",
                      action="append",
                      type=str,
                      default=[],
                      help="Paths to search for workflows, if not specified default is ./"
                      )
  parser.add_argument(
                      "-s", "--search_pattern",
                      action="append",
                      type=str,
                      default=[],
                      help="Search pattern used to find workflows, if not specified default is [*.json, *.py]"
                      )
  parser.add_argument(
                      "-r", "--run",
                      nargs="+",
                      type=str,
                      default=[],
                      help="Nodes in the workflow to run"
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
                      help="Save location for intermediary pickling and JSON serialization of actions/hosts"
                      )
  parser.add_argument(
                      "-v", "--verbose",
                      action="store_true",
                      help="Verbose output from actions running"
                      )
  return parser

def main():
  logger = sane.logger.Logger( "sane_runner" )
  parser  = get_parser()
  options = parser.parse_args()

  if len( options.path ) == 0:
    options.path = [ "./" ]

  if len( options.search_pattern ) == 0:
    options.search_pattern = [ "*.json", "*.py" ]

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

  orchestrator.verbose = options.verbose
  orchestrator.save_location = options.save_location

  if len( options.run ) > 0:
    orchestrator.run_actions( options.run, options.specific_host )

if __name__ == "__main__":
  main()
