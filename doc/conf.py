from datetime import date
from packaging.version import parse as version_parse
import feffdb

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.mathjax',
              'sphinxcontrib.video',
              'sphinx_copybutton',
              "sphinx_design",
              "nbsphinx"
]

project = 'feffdb'
copyright = f'2026, FeffDB Team, Argonne National Laboratory, The University of Chicago'


release = '0.1'  #version_parse(feffdb.__version__).base_version

html_title = "FeffDB: Database of Feff EXAFS calculations"
html_short_title = "FeffDB"



templates_path = ['_templates']
source_suffix = {'.rst': 'restructuredtext'}

exclude_trees = ['_build']
source_encoding = 'utf-8'
add_function_parentheses = True
add_module_names = True

pygments_style = 'sphinx'

html_theme = 'breeze'
html_theme_options = {"external_links": ["https://github.com/xraypy/feffdb"]}
html_static_path = ['_static']
html_use_index = True
html_show_sourcelink = True
