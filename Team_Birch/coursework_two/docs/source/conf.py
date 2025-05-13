# docs/source/conf.py

import os
import sys

# -- Project root and source path for autodoc/autodiscovery ------------------
# From docs/source, go up two levels into project root, then into src
sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------

project = "Coursework Two"
author = "Team Birch"
release = "1.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",      # Document functions and classes
    "sphinx.ext.napoleon",     # Google/NumPy docstring support
    "sphinx.ext.viewcode",     # Add links to source code
    "autoapi.extension",       # Auto-generate API reference
    "sphinx.ext.graphviz",     # Enable Graphviz diagrams
]

# -- AutoAPI configuration --------------------------------------------------
autoapi_type = "python"
autoapi_dirs = ["../../src/modules"]  # Path from docs/source to your Python modules
autoapi_root = "autoapi"              # Output directory for generated rst
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]

# never descend into third-party or Django code
autoapi_ignore = [
    "*/site-packages/*",
    "home*",
    "core*",
    "manage*",
    "django*",
    "jinja2*",
    "dotenv*",
]

# -- Paths and Templates -----------------------------------------------------
templates_path = ["_templates"]
exclude_patterns = []

# -- HTML output options ----------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# disable the built-in “Module index” pages
html_domain_indices = False
html_use_modindex    = False
