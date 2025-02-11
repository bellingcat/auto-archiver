# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import sys
import os
from importlib.metadata import metadata

sys.path.insert(0, os.path.abspath('../scripts'))
from scripts import generate_module_docs

# -- Project Hooks -----------------------------------------------------------
# convert the module __manifest__.py files into markdown files
generate_module_docs()


# -- Project information -----------------------------------------------------
package_metadata = metadata("auto-archiver")
project = package_metadata["name"]
authors = package_metadata["authors"]
release = package_metadata["version"]
language = 'en'

# -- General configuration ---------------------------------------------------
extensions = [
    "myst_parser",                  # Markdown support
    "autoapi.extension",            # Generate API documentation from docstrings
    "sphinxcontrib.mermaid",        # Mermaid diagrams
    "sphinx.ext.viewcode",          # Source code links
    "sphinx.ext.napoleon",          # Google-style and NumPy-style docstrings
    "sphinx.ext.autosectionlabel",
    # 'sphinx.ext.autosummary',       # Summarize module/class/function docs
]

templates_path = ['_templates']
exclude_patterns = []


# -- AutoAPI Configuration ---------------------------------------------------
autoapi_type = 'python'
autoapi_dirs = ["../../src/auto_archiver/core/", "../../src/auto_archiver/utils/"]
# get all the modules and add them to the autoapi_dirs
autoapi_dirs.extend([f"../../src/auto_archiver/modules/{m}" for m in os.listdir("../../src/auto_archiver/modules")])
autodoc_typehints = "signature"     # Include type hints in the signature
autoapi_ignore = ["*/version.py", ]                 # Ignore specific modules
autoapi_keep_files = True          # Option to retain intermediate JSON files for debugging
autoapi_add_toctree_entry = True    # Include API docs in the TOC
autoapi_python_use_implicit_namespaces = True
autoapi_template_dir = "../_templates/autoapi"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "imported-members",
]


# -- Markdown Support --------------------------------------------------------
myst_enable_extensions = [
    "deflist",              # Definition lists
    "html_admonition",      # HTML-style admonitions
    "html_image",           # Inline HTML images
    "replacements",         # Substitutions like (C)
    "smartquotes",          # Smart quotes
    "linkify",              # Auto-detect links
    "substitution",         # Text substitutions
]
myst_heading_anchors = 2
myst_fence_as_directive = ["mermaid"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_book_theme'
# html_static_path = ['_static']

