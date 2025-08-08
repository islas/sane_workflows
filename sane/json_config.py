import inspect

import sane.logger as logger
import sane.user_space as uspace


class JSONConfig( logger.Logger ):
  def __init__( self, **kwargs ):
    super().__init__( **kwargs )

  def load_config( self, config ):
    self.load_core_config( config )
    self.load_extra_config( config )
    self.check_unused( config )

  def check_unused( self, config ):
    unused = list( config.keys() )
    if len( unused ) > 0:
      self.log( f"Unused keys in config : {unused}", level=30 )

  def load_core_config( self, config ):
    pass

  def load_extra_config( self, config ):
    pass

  def search_type( self, type_str, noexcept=False ):
    module_name, class_name = type_str.split( ".", maxsplit=1 )
    tinfo = getattr( uspace.loaded_modules[module_name], class_name, None )
    if tinfo is None:
      msg = f"Could not find type <'{type_str}'> in {module_name}"
      self.log( msg, level=50 )
      if not noexcept:
        raise NameError( msg )
    return tinfo
