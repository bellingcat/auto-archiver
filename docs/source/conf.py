# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
from importlib.metadata import metadata

package_metadata = metadata("auto-archiver")
project = package_metadata["name"]
authors = package_metadata["authors"]
release = package_metadata["version"]


# -- General configuration ---------------------------------------------------
extensions = [
    "autoapi.extension",            # Generate API documentation from docstrings
    "myst_parser",                  # Markdown support
    'sphinxcontrib.mermaid',        # Mermaid diagrams
    "sphinx.ext.viewcode",          # Source code links
    "sphinx.ext.napoleon",          # Google-style and NumPy-style docstrings
    "sphinx.ext.autosectionlabel",
    # "sphinx.ext.autodoc",           # Include custom docstrings
    # 'sphinx.ext.autosummary',       # Summarize module/class/function docs
]

templates_path = ['_templates']
exclude_patterns = []


# -- AutoAPI Configuration ---------------------------------------------------
autoapi_type = 'python'
autoapi_dirs = ["../../src/auto_archiver/core/", "../../src/auto_archiver/utils/", "../../src/auto_archiver/modules/"]
autodoc_typehints = "signature"     # Include type hints in the signature
autoapi_ignore = ["*/version.py", ]                 # Ignore specific modules
autoapi_keep_files = False          # Option to retain intermediate JSON files for debugging
autoapi_add_toctree_entry = True    # Include API docs in the TOC
autoapi_python_use_implicit_namespaces = True
autoapi_template_dir = "../_templates/autoapi"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]


# -- Markdown Support --------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",          # ::: fences
    "deflist",              # Definition lists
    "html_admonition",      # HTML-style admonitions
    "html_image",           # Inline HTML images
    "replacements",         # Substitutions like (C)
    "smartquotes",          # Smart quotes
    "linkify",              # Auto-detect links
    "substitution",         # Text substitutions
]
myst_heading_anchors = 2

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Options for HTML output -------------------------------------------------
html_theme = 'furo'
# html_static_path = ['_static']

