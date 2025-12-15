from abc import ABCMeta, abstractmethod


class NameMatch( metaclass=ABCMeta ):
  def __init__( self, name, aliases=[], **kwargs ):
    self._name    = name
    self._aliases = list(set(aliases))
    super().__init__( **kwargs )

  @property
  def name( self ):
    """The name of this object set at instantiation"""
    return self._name

  @property
  def aliases( self ):
    """Aliases that this object may be referenced as"""
    return self._aliases.copy()

  @abstractmethod
  def match( self, requested_name ):
    return False

  def exact_match( self, requested_name ):
    return ( self._name == requested_name or requested_name in self._aliases )

  def partial_match( self, requested_name ):
    return (
            self._name in requested_name
            or next(
                    ( True for alias in self._aliases if alias in requested_name ),
                    False
                    )
            )
