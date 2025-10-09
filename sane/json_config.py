import inspect
import sys
import pydoc
import collections

import sane.logger as logger
import sane.user_space as uspace


def recursive_update( dest, source ):
  """Update mapping dest with source"""
  for k, v in source.items():
    if isinstance( v, collections.abc.Mapping ):
      dest[k] = recursive_update( dest.get( k, {} ), v )
    else:
      dest[k] = v
  return dest


class JSONConfig( logger.Logger ):
  def __new__( cls, *args, **kwargs ):
    # ideally this has (*args, **kwargs) but since this is the only class to have
    # a __new__ within all sane MRO, just dump the arguments
    instance = super( JSONConfig, cls ).__new__( cls )
    stack = inspect.stack()
    instance.__origin_instantiation__ = f"{stack[1][1]}:{stack[1][2]}"
    return instance

  def __init__( self, **kwargs ):
    super().__init__( **kwargs )
    self.__origin__ = [ sys.modules[self.__module__].__file__, self.__origin_instantiation__ ]

  def load_config( self, config : dict, origin : str=None ):
    if origin is not None: self.__origin__.append( str( origin ) )
    self.load_core_config( config, origin )
    self.load_extra_config( config, origin )
    self.check_unused( config )

  def check_unused( self, config : dict ):
    unused = list( config.keys() )
    if len( unused ) > 0:
      self.log( f"Unused keys in config : {unused}", level=30 )

  def load_core_config( self, config : dict, origin : str=None ):
    pass

  def load_extra_config( self, config : dict, origin : str=None ):
    pass

  @property
  def origins( self ):
    return self.__origin__.copy()

  def search_type( self, type_str : str, noexcept=False ):
    tinfo = pydoc.locate( type_str )
    if tinfo is not None:
      return tinfo

    # locate didn't work so try to use hinting
    if "." in type_str:
      module_name, class_name = type_str.rsplit( ".", maxsplit=1 )
    else:
      class_name = type_str
      module_name = ""

    for user_module_name, user_module in uspace.user_modules.items():
      if module_name in user_module_name:
        tinfo = getattr( user_module, class_name, None )
        if tinfo is not None:
          break

    if tinfo is None:
      msg = f"Could not find type <'{type_str}'> in {module_name}"
      self.log( msg, level=50 )
      if not noexcept:
        raise NameError( msg )
    return tinfo
