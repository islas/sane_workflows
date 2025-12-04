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

  def load_config( self, config : dict, origin : str = None ):
    """Base class implementation for loading of dict-based attributes into instance

    Take a config dict of relevant attributes and load them via :py:meth:`load_core_config`
    then :py:meth:`load_extra_config`. The config dict should be modified in each call
    to remove processed fields so that at the very end of this method, any unused
    keys in the config dict may be logged.

    The :py:meth:`load_extra_config` is meant as a user-overwritable method so that
    :py:meth:`load_core_config` may retain core underlying base class implementation
    details without the risk of base class loading not being called.

    To keep track of every time this function is called and potentially modifying
    this instance an origin may be provided, noting where the change is coming from.

    :param config: A dict of class-specific attributes.

      .. important::

            The config dict is modified such that only unused values are left in
            it at the end of this method
    :param origin: A string identifier of where this load is coming from
    """
    if origin is not None:
      self.__origin__.append( str( origin ) )
    self.load_core_config( config, origin )
    self.load_extra_config( config, origin )
    self.check_unused( config )

  def check_unused( self, config : dict ):
    unused = list( config.keys() )
    if len( unused ) > 0:
      self.log( f"Unused keys in config : {unused}", level=30 )

  def load_core_config( self, config : dict, origin : str = None ):
    """
    Any processed field should be removed from the ``config`` dict, with
    everything else ignored.

    See :py:meth:`load_config` for parameters.
    """
    pass

  def load_extra_config( self, config : dict, origin : str = None ):
    """Load any extra config options after :py:meth:`load_core_config`.

    Any processed field should be removed from the ``config`` dict, with
    everything else ignored.

    See :py:meth:`load_config` for parameters.
    """
    pass

  @property
  def origins( self ):
    """A copy of all the workflow file paths (and line numbers if applicable) that formed this object"""
    return self.__origin__.copy()

  def search_type( self, type_str : str, noexcept=False ):
    """Match a type (as an input string) to an actualy python :external:py:class:`type`

    If at any point a search is successful, the function immediately returns the
    found :external:py:class:`type`.

    Search priority:

    1. ``type_str`` using :external:py:mod:`pydoc` ``locate()`` (effectively search
       current context for fully qualified type name)
    2. Split ``type_str`` on last ``.`` in name and search any user-loaded module
       that contains the prefix for an attribute matching the suffix. If no split
       occurs all user modules are searched.

    Valid type examples:

    .. code-block:: python

        import sane
        import user_mod.nested.foo # module foo has CustomType

        # ... in the context of this class ...
        self.search_type( "sane.Action" )
        self.search_type( "sane.host.Host" )
        self.search_type( "user_mod.nested.foo.CustomType" )
        # Using search method (2) if foo was loaded into the user modules by the workflow
        # since "foo" is a substring of "user_mod.nested.foo"
        self.search_type( "foo.CustomType" )
    
    :return: :external:py:class:`type` corresponding to the ``type_str``
    """
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
