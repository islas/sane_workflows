import io
LABEL_LENGTH = 12

class Logger:
  def __init__( self, name ):
    self.logname_          = name
    self.labelIndentation_ = "  "
    self.labelLevel_       = 0
    self.label_            = "{0:<{1}}".format( "[{0}] ".format( self.logname_ ), LABEL_LENGTH + 3 )

  def log( self, *args, **kwargs ) :
    # https://stackoverflow.com/a/39823534
    output=io.StringIO()
    print( *args, file=output, end="", **kwargs )
    contents = output.getvalue()
    output.close()
    print( self.label_ + self.labelIndentation_ * self.labelLevel_ + contents, flush=True )
    return self.label_ + self.labelIndentation_ * self.labelLevel_ + contents
  
  def log_push( self, levels=1 ) :
    self.labelLevel_ += levels
  def log_pop( self, levels=1 ) :
    self.labelLevel_ -= levels
