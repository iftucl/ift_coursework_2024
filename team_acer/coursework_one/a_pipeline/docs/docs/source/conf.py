# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ift_coursework_group1'
copyright = '2025, kane basu,eren caliskan, rickey chen, jingyuan shi, zening xu, xiaohang yu, saif alarifi'
author = 'kane basu,eren caliskan, rickey chen, jingyuan shi, zening xu, xiaohang yu, saif alarifi'
release = '01'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys
autodoc_mock_imports = ["psycopg2", "boto3", "googleapiclient", "fastapi", "uvicorn"]
sys.path.insert(0, os.path.abspath('C:/Users/admin/Documents/GitHub/git-tutorial/ift_coursework_2024'))
sys.path.insert(0, os.path.abspath("C:/Users/admin/Documents/GitHub/git-tutorial/ift_coursework_2024/modules/app_writer"))
sys.path.insert(0, os.path.abspath('C:/Users/admin/Documents/GitHub/git-tutorial/ift_coursework_2024/modules/app_writer'))
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon'
]

html_theme = "sphinx_rtd_theme"

autodoc_mock_imports = ["psycopg2", "boto3", "googleapiclient"]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
