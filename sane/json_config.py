import inspect
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
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )

  def load_config( self, config : dict ):
    self.load_core_config( config )
    self.load_extra_config( config )
    self.check_unused( config )

  def check_unused( self, config : dict ):
    unused = list( config.keys() )
    if len( unused ) > 0:
      self.log( f"Unused keys in config : {unused}", level=30 )

  def load_core_config( self, config : dict ):
    pass

  def load_extra_config( self, config : dict ):
    pass

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
