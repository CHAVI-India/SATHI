# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html




# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'SATHI: Self Reported Assessment and Tracking for Health Insights'
copyright = '2026, CHAVI Team'
author = 'CHAVI Team'
release = 'Version 2.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

import os
import sys
import django

sys.path.insert(0, os.path.abspath('../..'))  # Assuming conf.py is in docs/source/
os.environ['DJANGO_SETTINGS_MODULE'] = 'chaviprom.settings'
django.setup()



extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',  
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
