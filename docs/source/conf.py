# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import toml


# Load project metadata from pyproject.toml to ensure single source of truth
project_metadata = toml.load("../../pyproject.toml")["project"]
project = project_metadata["name"]
authors = project_metadata["authors"]
release = project_metadata["version"]


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autoapi.extension",        # Generate API documentation from docstrings
    "myst_parser",              # Markdown support
    'sphinxcontrib.mermaid',    # Mermaid diagrams
    "sphinx.ext.autodoc",       #
    "sphinx.ext.viewcode",      # Source code links
    "sphinx.ext.napoleon",      # Google-style and NumPy-style docstrings
    'sphinx.ext.autosummary',   # Summarize module/class/function docs
]

templates_path = ['_templates']
exclude_patterns = []


# -- AutoAPI Configuration ---------------------------------------------------
# AutoAPI settings
autoapi_type = 'python'
autoapi_dirs = ["../../src"]
autodoc_typehints = "signature"    # Include type hints in the signature
# autoapi_ignore = []               # Ignore specific modules
# Note: Change to True to inspect files:
autoapi_keep_files = False          # Option to retain intermediate JSON files for debugging
autoapi_add_toctree_entry = True    # Include API docs in the TOC
autoapi_template_dir = None         # Use default templates
# Use templates here:
# autoapi_template_dir = "_templates/autoapi"


autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]



# Settings to parse Markdown files
myst_enable_extensions = [
    "colon_fence",   # Support for ::: fences
    "deflist",       # Definition lists
    "html_admonition",  # HTML-style admonitions
    "html_image",    # Inline HTML images
    "replacements",  # Substitutions like (C)
    "smartquotes",   # Smart quotes
    "linkify",       # Auto-detect links
    "substitution",  # Text substitutions
]
# If the Markdown file is not in the same directory, adjust paths as necessary
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']

# -- Additional configurations ------------------------------------------------
