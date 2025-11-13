import logging
import sys

from .action import Action, DependencyType, ActionState
from .environment import Environment
from .host import Host
from .hpc_host import HPCHost, PBSHost
from .orchestrator import Orchestrator, register
from .logger import DispatchingFormatter
from .user_space import user_modules

log_formatter = DispatchingFormatter(
    {
      f"{__name__}.logger" : logging.Formatter(
                                                fmt="%(asctime)s %(levelname)-8s %(message)s",
                                                datefmt="%Y-%m-%d %H:%M:%S"
                                                ),
      f"{__name__}.raw"    : logging.Formatter()
    },
    logging.Formatter( "%(message)s" )
  )
console_handler = logging.StreamHandler( sys.stdout )
console_handler.setFormatter( log_formatter )
internal_logger = logging.getLogger( __name__ )
internal_logger.setLevel( logging.INFO )
internal_logger.addHandler( console_handler )

logging.addLevelName( 25, "STDOUT" )
for i in range( logging.DEBUG, logging.INFO ):
  logging.addLevelName( i, f"DEBUG {i}" )

def log_exceptions( etype, value, traceback ):
  from traceback import format_exception
  lines = format_exception( etype, value, traceback )
  for line in lines:
    internal_logger.log( 50, line )
