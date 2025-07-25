from typing import TypeVar, Generic, Dict
from collections import UserDict

T = TypeVar( "T" )
class UniqueTypedDict( UserDict, Generic[T] ):
  def __init__( self, orig_type : T ):
    # This is to get around type obfuscation at runtime without relying on python 3.8+
    # features of __origin__ or __orig_class__
    self._original_type = orig_type
    super().__init__()

  def __setitem__( self, key, value : T ):
    if not isinstance( value, self._original_type ):
      msg = f"Error: Provided value to {UniqueTypedDict.__setitem__.__name__}() is not of type {self._original_type}"
      raise Exception( msg )

    # We know we have an action type
    if key not in self.data:
      super().__setitem__( key, value )
    else:
      msg = f"Error: Provided key ( \"{key}\" ) to {UniqueTypedDict.__setitem__.__name__}() does not have a unique value"
      raise Exception( msg )
