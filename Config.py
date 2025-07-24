from abc import ABCMeta, abstractmethod

class Config( metaclass=ABCMeta ):
  def __init__( self, name, aliases=[] ):
    self.name_    = name
    self.aliases_ = list(set(aliases))

  @abstractmethod
  def match( self, requested_config ):
    return False

  def exact_match( self, requested_config ):
    return ( self.name_ == requested_config or requested_config in self.aliases_ )

  def partial_match( self, requested_config ):
    return ( self.name_ in requested_config or next( ( True for alias in self.aliases_ if alias in requested_config ), False ) )
