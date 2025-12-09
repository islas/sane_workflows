# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import importlib
import inspect
import os
from sphinx_pyproject import SphinxConfig

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
config = SphinxConfig("../../pyproject.toml", globalns=globals())

project = "SANE Workflows"
copyright = "2025, islas"
author = "islas"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
              "sphinx.ext.autodoc",
              "sphinx.ext.autosummary",
              "sphinx.ext.linkcode",
              "sphinx.ext.intersphinx",
              # External extensions
              "myst_parser", # .md include
              "sphinx_toolbox.collapse",            # collapse sections
              "sphinx_toolbox.decorators",          # py:deco doesn't work
              "sphinx_toolbox.more_autodoc.regex"   # regex highlighting
              ]

templates_path = ["_templates"]
exclude_patterns = [ "links.rst" ]

autodoc_class_signature = "separated"
autodoc_typehints = "description"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
                      "prev_next_buttons_location": "bottom",
                      "style_external_links": True,
                      # Toc options
                      "collapse_navigation": False,
                      "sticky_navigation": True,
                      "navigation_depth": 4,
                      "includehidden": True,
                      "titles_only": False
                      }
# Pull in types and links from elsewhere
intersphinx_mapping = {
                        "python" : ( "https://docs.python.org/3/", None )
                      }

# Add global links
rst_epilog = ""
with open( "links.rst" ) as f:
  rst_epilog += f.read()

# Excellent solution from
# https://github.com/readthedocs/sphinx-autoapi/issues/202#issuecomment-907582382
code_url = f"https://github.com/islas/sane_workflows/tree/v{version}"
def linkcode_resolve(domain, info):
  if domain != "py":
    return None

  module = importlib.import_module(info["module"])
  if "." in info["fullname"]:
    objname, attrname = info["fullname"].split(".")
    obj = getattr( module, objname )
    try:
      # object is a method of a class
      obj = getattr( obj, attrname )
    except AttributeError:
      # object is an attribute of a class
      return None
  else:
    obj = getattr(module, info["fullname"])

  try:
    file = inspect.getsourcefile(obj)
    lines = inspect.getsourcelines(obj)
  except TypeError:
    # e.g. object is a typing.Union
    return None
  
  project_path = os.path.abspath( os.path.join( __file__, "../../../" ) )
  file = os.path.relpath(file, project_path )

  start, end = lines[1], lines[1] + len(lines[0]) - 1
  return f"{code_url}/{file}#L{start}-L{end}"
