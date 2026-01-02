import os
import sys
from datetime import datetime

# Add repo root so relative imports resolve
project_root = os.path.abspath('../../..')
sys.path.insert(0, project_root)

# Add packaged library src directory for autodoc (agent_framework.* modules)
library_src = os.path.join(project_root, 'agent-framework-pypi', 'src')
if os.path.isdir(library_src):
    sys.path.insert(0, library_src)

# Still expose bi_tools for domain example references
bi_tools_path = os.path.join(project_root, 'bi_tools')
if os.path.isdir(bi_tools_path):
    sys.path.insert(0, bi_tools_path)

project = 'AI Agent Framework'
author = 'Project Authors'
current_year = datetime.now().year
copyright = f'{current_year}, {author}'

# Version info
version = '2.2'
release = '2.2.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'myst_parser',
]

# Napoleon settings for better docstring parsing
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

templates_path = ['_templates']
exclude_patterns: list[str] = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
