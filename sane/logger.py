import io
import logging
import re

DEFAULT_LABEL_LENGTH = 22
STDOUT   = 18
ACT_INFO = 19
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


class Logger:
  def __init__( self, logname, **kwargs ):
    self._logname           = logname
    self._level_indentation = "  "
    self._level             = 0
    self._label             = ""
    self._logscope_stack    = []
    self.label_length       = DEFAULT_LABEL_LENGTH
    self.default_log_level  = logging.INFO
    self.logger             = None
    self.pop_logscope()

    super().__init__( **kwargs )

  @property
  def logname( self ):
    return self._logname

  @logname.setter
  def logname( self, logname ):
    self._logname = logname
    self._set_label( self.current_logname )

  def push_logscope( self, scope ):
    self._logscope_stack.append( scope )
    self._set_label( self.current_logname )

  def pop_logscope( self ):
    if len( self._logscope_stack ) > 0:
      self._logscope_stack.pop()
    self._set_label( self.current_logname )

  @property
  def current_logname( self ):
    return self._logname if len( self._logscope_stack ) == 0 else f"{self._logname}::{self._logscope_stack[-1]}"

  def _set_label( self, name ):
    self._label             = "{0:<{1}}".format( "[{0}] ".format( name ), self.label_length + 3 )

  def log( self, *args, level=None, **kwargs ) :
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
    self._level += levels

  def log_pop( self, levels=1 ):
    self._level -= levels

  def log_flush( self ):
    for handler in logger.handlers:
      handler.flush()
