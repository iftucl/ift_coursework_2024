import os
import sys
sys.path.insert(0, os.path.abspath('.'))

project = 'Magnolia ESG Extraction'
author = 'Magnolia'
release = '1.0'

extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax"
]
templates_path = ['_templates']
exclude_patterns = []

html_theme = 'alabaster'
html_static_path = ['_static']

autosectionlabel_prefix_document = True
numfig = True
