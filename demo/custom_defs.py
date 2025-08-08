import sane


class MyAction( sane.Action ):
  def __init__( self, id ):
    super().__init__( id )

  def calc_fib( self, x ):
    if x <= 1 : return x
    prev_0 = 0
    prev_1 = 1
    for i in range( 2, x + 1 ):
      tmp = prev_0 + prev_1
      prev_0 = prev_1
      prev_1 = tmp
    return prev_1

  def run( self ):
    self.log( "Inside my custom run" )
    x = 12
    self.log( f"Fibonacci number @ {x} = {self.calc_fib(x)}" )
    return 0

class MyActionWithArgs( MyAction ):
  def __init__( self, id ):
    super().__init__( id )

  def run( self ):
    self.log( "Inside my custom run with arguments used" )
    if "arguments" in self.config:
      for x in self.config["arguments"]:
        self.log( f"Fibonacci number @ {x} = {self.calc_fib(x)}" )
    else:
      self.log( "Please provide arguments", level=30 )
    return 0

@sane.register
def test( orchestrator ):
  act = MyAction( "foobarbarfoo" )
  orchestrator.log( type( act ) )
