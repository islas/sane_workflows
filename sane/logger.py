import io
LABEL_LENGTH = 12

class Logger:
  def __init__( self, name ):
    self._logname           = name
    self._level_indentation = "  "
    self._level             = 0
    self._label             = "{0:<{1}}".format( "[{0}] ".format( self._logname ), LABEL_LENGTH + 3 )

  def log( self, *args, **kwargs ) :
    # https://stackoverflow.com/a/39823534
    output=io.StringIO()
    print( *args, file=output, end="", **kwargs )
    contents = output.getvalue()
    output.close()
    print( self._label + self._level_indentation * self._level + contents, flush=True )
    return self._label + self._level_indentation * self._level + contents
  
  def log_push( self, levels=1 ) :
    self._level += levels
  def log_pop( self, levels=1 ) :
    self._level -= levels
