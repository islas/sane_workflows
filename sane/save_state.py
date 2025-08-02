import os
import pickle


def load( filename ):
  obj = None
  with open( filename, "rb" ) as f:
    obj = pickle.load( f )
  return obj


class SaveState:
  def __init__( self, filename, path="./", **kwargs ):
    self._filename      = filename
    self._save_location = os.path.abspath( path )
    super().__init__( **kwargs )

  @property
  def save_file( self ):
    return os.path.abspath( f"{self.save_location}/{self._filename}" )

  @property
  def save_location( self ):
    return self._save_location

  @save_location.setter
  def save_location( self, path ):
    self._save_location = os.path.abspath( path )

  def save( self ):
    with open( self.save_file, "wb" ) as f:
      pickle.dump( self, f )
