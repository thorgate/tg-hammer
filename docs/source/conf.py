import os

from hammer import hammer_version


on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# -- General configuration ------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
]
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = u'tg-hammer'
copyright = u'2015, Thorgate'
author = u'Thorgate'
version = hammer_version
release = hammer_version
exclude_patterns = []
pygments_style = 'sphinx'
todo_include_todos = False

if not on_rtd:
    import sphinx_rtd_theme

    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
