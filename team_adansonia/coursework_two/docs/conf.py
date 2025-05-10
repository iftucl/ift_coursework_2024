# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

# Try importing the module to check if the path is correct
try:
    import coursework_two
    print("Module imported successfully")
except ImportError as e:
    print("Error importing module:", e)

project = 'Team Adansonia'
copyright = '2025, Balazs'
author = 'Balazs'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",      # Automatically include docstrings
    "sphinx.ext.napoleon",     # Support for Google/NumPy docstrings
    "sphinx.ext.viewcode",     # Add links to highlighted source code
    "sphinx.ext.todo",         # Support for todo:: directives
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
# conf.py
autosummary_generate = True  # Automatically generate summaries for modules

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
