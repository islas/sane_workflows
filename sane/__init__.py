import logging
import sys

from .action import Action, DependencyType, ActionState
from .environment import Environment
from .host import Host
from .orchestrator import Orchestrator, register


log_formatter = logging.Formatter(
                                  fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )
console_handler = logging.StreamHandler( sys.stdout )
console_handler.setFormatter( log_formatter )
internal_logger = logging.getLogger( __name__ )
internal_logger.setLevel( logging.INFO )
internal_logger.addHandler( console_handler )
