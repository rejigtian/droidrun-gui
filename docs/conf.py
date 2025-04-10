import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'DroidRun'
copyright = '2025, Bonny Network'
author = 'Niels Schmidt'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
add_module_names = False 