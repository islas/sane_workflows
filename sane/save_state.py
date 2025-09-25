import json
import os
import pickle
import importlib
import sys

import sane.user_space as uspace


def load( filename ):
  state = None
  with open( filename, "r" ) as f:
    state = json.load( f )

  sys.path.extend( state["import_paths"] )
  importlib.import_module( state["module"] )

  obj = None
  with open( state["pickle_file"], "rb" ) as f:
    obj = pickle.load( f )
  return obj


class SaveState:
  def __init__( self, filename, base, path="./", **kwargs ):
    self._filename      = filename
    self._save_location = os.path.abspath( path )
    self._base          = base
    self.import_paths   = uspace.user_paths
    super().__init__( **kwargs )

  @property
  def file_basename( self ):
    return os.path.abspath( f"{self.save_location}/{self._filename}" )

  @property
  def pickle_file( self ):
    return self.file_basename + ".pkl"

  @property
  def save_file( self ):
    return self.file_basename + ".json"

  @property
  def save_location( self ):
    return self._save_location

  @save_location.setter
  def save_location( self, path ):
    self._save_location = os.path.abspath( path )

  def save( self ):
    with open( self.pickle_file, "wb" ) as f:
      pickle.dump( self, f )

    state = { "pickle_file" : self.pickle_file, "module" : self.__module__, "import_paths" : self.import_paths }
    with open( self.save_file, "w" ) as f:
      json.dump( state, f, indent=2 )
