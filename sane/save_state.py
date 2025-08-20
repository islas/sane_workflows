import collections
import inspect
import json
import os
import pickle
import sys
import types


def load( filename ):
  state = None
  with open( filename, "r" ) as f:
    state = json.load( f )

  _load_definitions( state["source"] )

  obj = None
  with open( state["pickle_file"], "rb" ) as f:
    obj = pickle.load( f )
  return obj


def _load_definitions( source_dict ):
  # THIS IS THE DANGEROUS PART
  for module_name, class_dict in source_dict.items():
    # Load in this module manually by in situ creating the module and source def
    if module_name not in sys.modules:
      module = types.ModuleType( module_name )
      sys.modules[module_name] = module
      # Auto-import ourselves
      exec( "import sane\n", sys.modules[module_name].__dict__ )

    for class_name, source in class_dict.items():
      exec( source, sys.modules[module_name].__dict__ )


class SaveState:
  def __init__( self, filename, base, path="./", **kwargs ):
    self._filename      = filename
    self._save_location = os.path.abspath( path )
    self._base          = base
    super().__init__( **kwargs )

    # Make sure anything derived will save using this class
    # copyreg.pickle( type( self ), SaveState.__reduce__ )
    # self._source_dict   = self._get_class_definitions()

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

    source_dict = self._get_class_definitions()
    state = { "pickle_file" : self.pickle_file, "source" : source_dict }
    with open( self.save_file, "w" ) as f:
      json.dump( state, f, indent=2 )

  def _get_class_definitions( self ):
    tinfo = type( self )
    all_ancestors  = inspect.getmro( tinfo )
    base_ancestors = inspect.getmro( self._base )
    source_dict = collections.OrderedDict()
    for base_class in reversed( all_ancestors ):
      if base_class != self._base and base_class not in base_ancestors:
        fq_name = f"{base_class.__module__}.{base_class.__name__}"
        if base_class.__module__ not in source_dict:
          source_dict[ base_class.__module__ ] = collections.OrderedDict()

        source = inspect.getsource( base_class )
        source_dict[base_class.__module__][base_class.__name__] = source

    # Now get actual class
    if tinfo != self._base:
      if tinfo.__module__ not in source_dict:
        source_dict[ tinfo.__module__ ] = collections.OrderedDict()

      source = inspect.getsource( tinfo )
      source_dict[tinfo.__module__][tinfo.__name__] = source

    return source_dict
