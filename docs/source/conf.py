# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Make sure the project is in the path for autodoc
import os
import sys
sys.path.append(os.path.abspath("../.."))
sys.path.append(os.path.abspath("_ext"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'pzp-hardware'
copyright = '2025, jdranczewski'
author = 'jdranczewski'
release = '0.2.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "pzp_requirements"
]

templates_path = ['_templates']
exclude_patterns = []

autodoc_default_options = {
    "member-order": "bysource",
    "exclude-members": (
        "define_params, define_actions, define_readouts, "
        "setup, handle_close, custom_layout, "
        "custom_horizontal, param_wrap, action_wrap"
    )
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
#html_static_path = ['_static']
