from abc import ABCMeta, abstractmethod

class Config( metaclass=ABCMeta ):
  def __init__( self, name, aliases=[] ):
    self._name    = name
    self._aliases = list(set(aliases))

  @property
  def name( self ):
    return self._name
  
  @property
  def aliases( self ):
    return self._aliases.copy()

  @abstractmethod
  def match( self, requested_config ):
    return False

  def exact_match( self, requested_config ):
    return ( self._name == requested_config or requested_config in self._aliases )

  def partial_match( self, requested_config ):
    return ( self._name in requested_config or next( ( True for alias in self._aliases if alias in requested_config ), False ) )
