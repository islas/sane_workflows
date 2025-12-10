import logging
import sys

from .action import Action, DependencyType, ActionState, ActionStatus
from .environment import Environment
from .host import Host
from .hpc_host import HPCHost, PBSHost
from .orchestrator import Orchestrator, register
from .logger import DispatchingFormatter, ParentLevelFilter, MAIN_LOG, STDOUT
from .user_space import user_modules

log_formatter = DispatchingFormatter(
    {
      f"{__name__}[.]logger" : logging.Formatter(
                                                fmt="%(asctime)s %(levelname)-8s %(message)s",
                                                datefmt="%Y-%m-%d %H:%M:%S"
                                                ),
      f"{__name__}[.]action" : logging.Formatter(
                                                fmt="%(asctime)s %(levelname)-8s %(message)s",
                                                datefmt="%Y-%m-%d %H:%M:%S"
                                                ),
      f"{__name__}[.]action[.].*[.]raw" : logging.Formatter()
    },
    logging.Formatter( "%(message)s" )
  )
console_handler = logging.StreamHandler( sys.stdout )
console_handler.setFormatter( log_formatter )
internal_logger = logging.getLogger( __name__ )
internal_logger.setLevel( MAIN_LOG )
internal_logger.addHandler( console_handler )
action_logger = internal_logger.getChild( f"action" )
action_logger.setLevel( STDOUT )

# Filter any logging from lower loggers if they do not meet our threshold
internal_filter = ParentLevelFilter()
internal_filter.logger = internal_logger

console_handler.addFilter( internal_filter )

def log_exceptions( etype, value, traceback ):
  from traceback import format_exception
  lines = format_exception( etype, value, traceback )
  for line in lines:
    internal_logger.log( 50, line )
