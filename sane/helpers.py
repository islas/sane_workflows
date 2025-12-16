import functools
import collections


def copydoc( *funcs, append=True, module=None ):
  """Copy docstrings from funcs"""
  def mod_doc( orig ):
    prefix = "\n**From** :py:meth:`{function}`:\n\n"

    orig_prefix = prefix.format( function=orig.__qualname__ )
    if not hasattr( orig, "__orig_doc__" ):
      orig.__orig_doc__ = orig.__doc__

    if orig.__orig_doc__ is not None and orig_prefix not in orig.__doc__:
      orig.__doc__ = orig_prefix + orig.__orig_doc__

    full_doc = orig.__doc__
    
    for f in funcs:
      if not hasattr( f, "__orig_doc__" ):
        f.__orig_doc__ = f.__doc__

      if f.__orig_doc__ is not None:
        func_str = f.__qualname__ + ( f" <{module}.{f.__qualname__}>" if module is not None else "" )
        f_doc = prefix.format( function=func_str ) + f.__orig_doc__
        full_doc = ( full_doc if append else f_doc ) + ( f_doc if append else full_doc )
    orig.__doc__ = full_doc
    return orig
  return mod_doc


def recursive_update( dest : dict, source : dict ) -> dict:
  """Update mapping ``dest`` with ``source``, recursively updating any nested mapping instance
  
  This will update/override any value in ``dest`` with the value that is present in ``source``.
  If the value in ``source`` is a mapping (``dict``) then the key for which this is being
  updated within ``dest`` is updated recursively, defaulting to an empty ``dict`` if that
  key does not exist yet.
  """
  for k, v in source.items():
    if isinstance( v, collections.abc.Mapping ):
      dest[k] = recursive_update( dest.get( k, {} ), v )
    else:
      dest[k] = v
  return dest
