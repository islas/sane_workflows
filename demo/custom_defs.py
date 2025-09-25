import os

import sane
import sane.json_config as jconfig

class MyAction( sane.Action ):
  def __init__( self, id ):
    super().__init__( id )

  def calc_fib( self, x ):
    if x <= 1:
      return x
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
    self.dummy = jconfig.JSONConfig( logname="foo" )


  def run( self ):
    self.log( "Inside my custom run with arguments used" )
    self.log( f"cwd : '{os.getcwd()}'" )
    if "arguments" in self.config:
      for x in self.config["arguments"]:
        self.log( f"Fibonacci number @ {x} = {self.calc_fib(x)}" )
    else:
      self.log( "Please provide arguments", level=30 )

    self.log( self.dummy.check_unused )
    self.log( jconfig.JSONConfig )
    return 0


class MyActionWithMult( MyActionWithArgs ):
  def __init__( self, id ):
    self.mult = 1
    super().__init__( id )

  def load_extra_config( self, config ):
    mult = config.pop( "mult", 1 )
    if mult > 1:
      self.mult = mult
    # Make sure to call any inherited config reading
    super().load_extra_config( config )

  def setup( self ):
    self.log( f"Modifying args with mult = {self.mult}" )
    if "arguments" in self.config:
      self.config["arguments"] = [ x * self.mult for x in self.config["arguments"] ]


@sane.register
def test( orchestrator ):
  act = MyAction( "foobarbarfoo" )
  orchestrator.log( type( act ) )
