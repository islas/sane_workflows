import io
import logging
import re
import sys


DEFAULT_LABEL_LENGTH = 22
#: The log level any stdout captured in :py:class:`Action` or :py:class:`Environment` is output at
STDOUT   = 18
#: The default log level of :py:meth:`Action.log`,
#: i.e. the log level most :py:class:`Action` activity is output at
ACT_INFO = 19
#: The default log level needed to output to the main logfile/console
MAIN_LOG = 20

logger = logging.getLogger( __name__ )

logging.addLevelName( STDOUT,   "STDOUT" )
logging.addLevelName( ACT_INFO, "INFO" )
for i in range( logging.DEBUG, logging.INFO - 2 ):
  logging.addLevelName( i, f"DEBUG {i}" )


# https://stackoverflow.com/a/34626685
class DispatchingFormatter:
  def __init__(self, formatters, default_formatter):
    self._formatters = formatters
    self._default_formatter = default_formatter

  def format(self, record):
    formatter = None
    max_span  = 0
    for fmt in self._formatters.keys():
      found = re.match( fmt, record.name )
      if found is not None:
        span = found.span()[1] - found.span()[0]
        if span > max_span:
          formatter = self._formatters[fmt]

    if formatter is None:
      formatter = self._default_formatter
    return formatter.format(record)


class ParentLevelFilter( logging.Filter ):
  def filter( self, record ):
    # Only allow the record to pass if its level is >= the parent's effective level
    return record.levelno >= self.logger.getEffectiveLevel()


# Initialize logging setup for package
log_formatter = DispatchingFormatter(
    {
      f"sane[.]logger" : logging.Formatter(
                                                fmt="%(asctime)s %(levelname)-8s %(message)s",
                                                datefmt="%Y-%m-%d %H:%M:%S"
                                                ),
      f"sane[.]action" : logging.Formatter(
                                                fmt="%(asctime)s %(levelname)-8s %(message)s",
                                                datefmt="%Y-%m-%d %H:%M:%S"
                                                ),
      f"sane[.]action[.].*[.]raw" : logging.Formatter()
    },
    logging.Formatter( "%(message)s" )
  )
console_handler = logging.StreamHandler( sys.stdout )
console_handler.setFormatter( log_formatter )
internal_logger = logging.getLogger( "sane" )
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


class Logger:
  def __init__( self, logname, **kwargs ):
    self._logname           = logname
    self._level_indentation = "  "
    self._level             = 0
    self._label             = ""
    self._logscope_stack    = []

    #: Pad length to use for generating message prefix (logname and scope)
    self.label_length       = DEFAULT_LABEL_LENGTH

    #: The default log level to use when no explicit level is provided to :py:meth:`log`
    self.default_log_level  = logging.INFO
    self.logger             = None
    self.pop_logscope()

    super().__init__( **kwargs )

  @property
  def logname( self ):
    """The current base logname of this object"""
    return self._logname

  @logname.setter
  def logname( self, logname ):
    self._logname = logname
    self._set_label( self.current_logname )

  def push_logscope( self, scope ):
    """Push a scope context string onto the stack

    Adding scope context causes subsequent log messages to be suffixed with the
    current scope as <:py:attr:`logname`>::<current scope>
    """
    self._logscope_stack.append( scope )
    self._set_label( self.current_logname )

  def pop_logscope( self ):
    """Pop a scope context string from the stack

    Removing scope context causes subsequent messages to resume with the previous
    scope if present, or return to the original :py:attr:`logname` only.
    """
    if len( self._logscope_stack ) > 0:
      self._logscope_stack.pop()
    self._set_label( self.current_logname )

  @property
  def current_logname( self ):
    """Give the current logname as would appear in messages, including scope context"""
    return self._logname if len( self._logscope_stack ) == 0 else f"{self._logname}::{self._logscope_stack[-1]}"

  def _set_label( self, name ):
    """Internal string used to construct log messages, only changes on scope or logname change"""
    self._label             = "{0:<{1}}".format( "[{0}] ".format( name ), self.label_length + 3 )

  def log( self, *args, level : int = None , **kwargs ) :
    """Wrapper function around :external:py:meth:`logging.Logger.log`

    The ``args`` and ``kwargs`` parameters gets passed to :external:py:func:`print()`
    redirected into a string. The string is prefixed with [<:py:attr:`current_logname`>]
    and is then logged out using the current internal :external:py:class:`logging.Logger`
    and any format that logger applies.

    :param level: the `logging level`_ the message should be output as, default is :py:attr:`default_log_level`
    """
    if level is None:
      level = self.default_log_level
    if self.logger is None:
      self.logger = logger

    # https://stackoverflow.com/a/39823534
    output = io.StringIO()
    print( *args, file=output, end="", **kwargs )
    contents = output.getvalue()
    output.close()
    self.logger.log( level, self._label + self._level_indentation * self._level + contents )
    # Might need to find a way to flush...
    # self._console_handler.flush()
    return self._label + self._level_indentation * self._level + contents

  def log_push( self, levels=1 ):
    """Add a level of indentation to subsequent messages"""
    self._level += levels

  def log_pop( self, levels=1 ):
    """Remove a level of indentation to subsequent messages"""
    self._level -= levels

  def log_flush( self ):
    """Force flush all handlers associated with the internal :external:py:class:`logging.Logger`"""
    for handler in self.logger.handlers:
      handler.flush()
