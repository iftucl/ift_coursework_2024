# -- Project information -----------------------------------------------------
project = 'cw2'
copyright = '2025, team_ginkgo'
author = 'team_ginkgo'
release = '1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# 让 Sphinx 知道去哪里找模块
import os
import sys
sys.path.insert(0, os.path.abspath('../modules'))

# -- Options for HTML output -------------------------------------------------
html_theme = 'alabaster'
html_static_path = ['_static']
