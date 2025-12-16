#!/usr/bin/env python3
import argparse
import os
import sys

import json
import math


def squarest_divisors( n ):
  x = round( math.sqrt( n ) )
  while n % x > 0:
    x -= 1
  return x, n // x


def plot_resource_usage( start_time, ax, resource, resource_log, arrow_deltas, stem_timeline ):
  import datetime

  import matplotlib.dates as mdates

  import sane

  ntimes = 12
  ax.set_title( resource, rotation=90, x=1.05, y=0.5, va="center" )
  use_plot_times = [mdates.date2num( datetime.datetime.fromisoformat( start_time ) )]
  use_plot_vals  = [0]
  acq_plot_times = []
  acq_plot_vals  = []
  acq_plot_used  = []
  acq_amount_max = 0
  rel_plot_times = []
  rel_plot_vals  = []
  rel_plot_used  = []
  rel_amount_max = 0

  for action, amount, timestamp, used in resource_log["acquire"]:
    acq_amount_max = max( acq_amount_max, used )
    acq_plot_times.append( mdates.date2num( datetime.datetime.fromisoformat( timestamp ) ) )
    acq_plot_vals.append( amount )
    acq_plot_used.append( used )
    use_plot_times.append( acq_plot_times[-1] )
    use_plot_vals.append( used )
  for action, amount, timestamp, used in resource_log["release"]:
    rel_amount_max = max( rel_amount_max, amount )
    rel_plot_times.append( mdates.date2num( datetime.datetime.fromisoformat( timestamp ) ) )
    rel_plot_vals.append( -amount )
    rel_plot_used.append( used )
    use_plot_times.append( rel_plot_times[-1] )
    use_plot_vals.append( used )

  res = sane.resources.res_size_reduce( { "numeric" : max( acq_amount_max, rel_amount_max ), "unit" : resource_log["unit"], "scale" : "" } )
  scale = sane.resources._multipliers[res["scale"]]
  
  use_plot_vals = list( map( lambda val: val / scale, use_plot_vals ) )
  acq_plot_vals = list( map( lambda val: val / scale, acq_plot_vals ) )
  acq_plot_used = list( map( lambda val: val / scale, acq_plot_used ) )
  rel_plot_vals = list( map( lambda val: val / scale, rel_plot_vals ) )
  rel_plot_used = list( map( lambda val: val / scale, rel_plot_used ) )

  # Sort values
  use_plot_vals = [ x for _, x in sorted( zip(use_plot_times, use_plot_vals), key=lambda pair: pair[0] ) ]
  acq_plot_vals = [ x for _, x in sorted( zip(acq_plot_times, acq_plot_vals), key=lambda pair: pair[0] ) ]
  acq_plot_used = [ x for _, x in sorted( zip(acq_plot_times, acq_plot_used), key=lambda pair: pair[0] ) ]
  rel_plot_vals = [ x for _, x in sorted( zip(rel_plot_times, rel_plot_vals), key=lambda pair: pair[0] ) ]
  rel_plot_used = [ x for _, x in sorted( zip(rel_plot_times, rel_plot_used), key=lambda pair: pair[0] ) ]

  use_plot_times = sorted( use_plot_times )
  ax.step( sorted( use_plot_times ), use_plot_vals, where="post", c="b" )

  acq_plot_times = sorted( acq_plot_times )
  rel_plot_times = sorted( rel_plot_times )
  if stem_timeline:
    ax.stem( acq_plot_times, acq_plot_vals, linefmt="C3-", markerfmt="^" )
    ax.stem( rel_plot_times, rel_plot_vals, linefmt="C1-", markerfmt="v" )

  time_range = use_plot_times[-1] - use_plot_times[0]
  if arrow_deltas:
    acq_start = [ used - val for used, val in zip( acq_plot_used, acq_plot_vals ) ]
    rel_start = [ used - val for used, val in zip( rel_plot_used, rel_plot_vals ) ]
    ax.quiver( 
              acq_plot_times, acq_start, [0] * len( acq_plot_used ), acq_plot_vals,
              scale_units="xy", scale=1, angles="xy", minlength=0.01,
              headwidth=4, headlength=4, headaxislength=3.5, width=0.001,
              color="red"
              )
    ax.quiver( 
              rel_plot_times, rel_start, [0] * len( rel_plot_used ), rel_plot_vals,
              scale_units="xy", scale=1, angles="xy", minlength=0.01,
              headwidth=4, headlength=4, headaxislength=3.5, width=0.001,
              color="green"
              )

  ax.set_ylim( -rel_amount_max / scale * 1.1, acq_amount_max / scale * 1.1)
  ax.set_ylabel( res["scale"] + res["unit"] )
  time_xtick = [ use_plot_times[0] + (use_plot_times[-1] - use_plot_times[0]) / ntimes * i for i in range( ntimes + 1 ) ]
  time_label = [ str(mdates.num2timedelta( t - use_plot_times[0] )) for t in time_xtick ]

  ax.set_xticks( time_xtick, labels=[ t.split(".")[0] for t in  time_label], rotation=30 )

def plot_usage( workflow_save, arrow_deltas, stem_timeline ):
  import matplotlib.pyplot as plt

  resource_logs = json.load( open( workflow_save, "r" ) )["resource_usage"]
  resource_logs.pop( "null", None )

  times = list( resource_logs.keys() )
  print( f"index   time" )
  for i, t in enumerate( times ):
    print( f"{i:<5}   {t}" )

  view_time = input( "View time index [default 0]: " )
  try:
    view_time = int( view_time )
  except ValueError:
    view_time = 0
  print( f"Viewing resource usage for time {times[view_time]}")

  workflow_run = resource_logs[times[view_time]]
  for host in workflow_run:
    simple = True
    first  = next(iter(workflow_run[host].values()))
    plots  = []
    if "release" not in first and "acquire" not in first:
      simple = False
      plots = set( [ p for p, pdict in workflow_run[host].items() for q, qdict in pdict.items() if qdict["acquire"] ] )
    else:
      plots = [ p for p, pdict in workflow_run[host].items() if pdict["acquire"] ]
    nx, ny = squarest_divisors( len( plots ) )
    fig = plt.figure()
    fig.suptitle( times[view_time], fontsize="x-large" )
    subfigs = fig.subfigures( nx, ny )
    if not isinstance( subfigs, list ):
      subfigs = [subfigs]

    for i, resource in enumerate( plots ):
      print( f"Plotting {resource}" )
      rdict = workflow_run[host][resource]
      subfigs[i].suptitle( resource, y=.94 )
      if simple:
        ax = subfigs[i].subplots()
        plot_resource_usage( times[view_time], ax, resource, rdict, arrow_deltas, stem_timeline )
      else:
        # nested provider
        subfigs[i].subplots_adjust( hspace=0.0 )
        subax = subfigs[i].subplots( len( rdict.keys() ), sharex=True, squeeze=False )
        for j, pool_resource in enumerate( rdict.items() ):
          plot_resource_usage( times[view_time], subax[j][0], pool_resource[0], pool_resource[1], arrow_deltas, stem_timeline )

  plt.show()


def show_status( workflow_save ):
  import sane
  actions = json.load( open( workflow_save, "r" ) )["actions"]
  longest_action = len( max( actions.keys(), key=len ) )
  statuses = [ f"{node:<{longest_action}}: " + actions[node]["status"] for node in actions.keys() ]
  sane.orchestrator.print_actions( statuses, max_line=150 )


def show_state( workflow_save ):
  import sane
  actions = json.load( open( workflow_save, "r" ) )["actions"]
  longest_action = len( max( actions.keys(), key=len ) )
  statuses = [ f"{node:<{longest_action}}: " + actions[node]["state"] for node in actions.keys() ]
  sane.orchestrator.print_actions( statuses, max_line=150 )


def get_parser():
  base = argparse.ArgumentParser( add_help=False )
  base.add_argument(
                    "workflow_save",
                    help="Location of workflow save (typically ./tmp/)",
                    type=str,
                    default="./tmp",
                    nargs="?"
                      )
  base.add_argument(
                    "-f", "--filename",
                    help="Use non-standard filename",
                    type=str,
                    default="orchestrator.json"
                    )
  parser = argparse.ArgumentParser()
  subparsers = parser.add_subparsers( required=True, dest="cmd" )
  usage   = subparsers.add_parser( "usage",  help="View resource usage", parents=[base] )
  status  = subparsers.add_parser( "status", help="View action status", parents=[base] )
  status  = subparsers.add_parser( "state",  help="View action state", parents=[base] )
  usage.add_argument(
                      "-a", "--arrows",
                      action="store_true",
                      help="Plot individual arrow events with the usage"
                      )
  usage.add_argument(
                      "-s", "--stems",
                      action="store_true",
                      help="Plot stem events at the bottom of the usage"
                      )
  return parser

def main():
  filepath = os.path.dirname( os.path.abspath( __file__ ) )
  package_path = os.path.abspath( os.path.join( filepath, ".." ) )
  if package_path not in sys.path:
      sys.path.append( package_path )

  import sane

  parser = get_parser()
  options = parser.parse_args()
  filename = os.path.join( options.workflow_save, options.filename )
  if options.cmd == "usage":
    plot_usage( filename, options.arrows, options.stems )
  elif options.cmd == "status":
    show_status( filename )
  elif options.cmd == "state":
    show_state( filename )

if __name__ == "__main__":
  main()
