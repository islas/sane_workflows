#!/usr/bin/env python3
import argparse
import os
import sys


def get_parser():
  # Keep direct execution from bin/ working before the package is installed.
  filepath = os.path.dirname( os.path.abspath( __file__ ) )
  package_path = os.path.abspath( os.path.join( filepath, ".." ) )
  if sys.path[0] != package_path:
    sys.path.insert( 0, package_path )

  from sane import sane_runner, sane_view

  parser = argparse.ArgumentParser( description="SANE workflow tools" )
  subparsers = parser.add_subparsers( dest="command" )
  # Python 3.6 requires setting this attribute after creating the subparsers.
  subparsers.required = True
  workflow = sane_runner.get_parser( subparsers.add_parser( "workflow", help="Orchestrate actions" ) )
  workflow.set_defaults( _parser=workflow )
  view = sane_view.get_parser( subparsers.add_parser( "view", help="Inspect a saved workflow" ) )
  view.set_defaults( _parser=view )
  return parser


def main():
  options = get_parser().parse_args()
  from sane import sane_runner, sane_view

  command = options.command
  # The runner serializes its namespace into CLI arguments for virtual relaunches.
  del options.command
  if command == "workflow":
    return sane_runner.main( options )
  elif command == "view":
    return sane_view.main( options )


if __name__ == "__main__":
  main()
