# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
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
              "myst_parser"
              ]

templates_path = ["_templates"]
exclude_patterns = []

autodoc_class_signature = "separated"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
