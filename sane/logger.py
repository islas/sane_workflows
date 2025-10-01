import io
import logging

LABEL_LENGTH = 18


# https://stackoverflow.com/a/34626685
class DispatchingFormatter:
  def __init__(self, formatters, default_formatter):
    self._formatters = formatters
    self._default_formatter = default_formatter

  def format(self, record):
    formatter = self._formatters.get(record.name, self._default_formatter)
    return formatter.format(record)


class Logger:
  def __init__( self, logname, **kwargs ):
    self._logname           = logname
    self._level_indentation = "  "
    self._level             = 0
    self._label             = ""
    self._logname_stack     = []
    self.restore_logname()
    self._logger = None

    super().__init__( **kwargs )

  @property
  def logname( self ):
    return self._logname

  def override_logname( self, name ):
    self._set_label( name )
    self._logname_stack.append( name )

  def restore_logname( self ):
    if len( self._logname_stack ) > 0:
      self._logname_stack.pop()
    self._set_label( self.last_logname )

  @property
  def last_logname( self ):
    return self._logname if len( self._logname_stack ) == 0 else self._logname_stack[-1]

  def _set_label( self, name ):
    self._label             = "{0:<{1}}".format( "[{0}] ".format( name ), LABEL_LENGTH + 3 )

  def log( self, *args, level=logging.INFO, **kwargs ) :
    if self._logger is None:
      self._logger = logging.getLogger( __name__ )
    # https://stackoverflow.com/a/39823534
    output = io.StringIO()
    print( *args, file=output, end="", **kwargs )
    contents = output.getvalue()
    output.close()
    self._logger.log( level, self._label + self._level_indentation * self._level + contents )
    # Might need to find a way to flush...
    # self._console_handler.flush()
    return self._label + self._level_indentation * self._level + contents

  def log_push( self, levels=1 ):
    self._level += levels

  def log_pop( self, levels=1 ):
    self._level -= levels

  def log_flush( self ):
    if self._logger is None:
      self._logger = logging.getLogger( __name__ )
    for handler in self._logger.handlers:
      handler.flush()
