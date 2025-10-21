# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import pathlib


project = "Graph Visualization for Python"
copyright = "2025, Neo4j, Inc."
author = "Neo4j, Inc."
release = "0.1.6"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # include docs from docstrings
    "enum_tools.autoenum",  # specialised autoclass for enums
    "sphinx.ext.napoleon",  # Support for NumPy and Google style docstrings
    "nbsphinx",  # support for jupyter notebooks
    "nbsphinx_link",  # support for jupyter notebooks from other directories
]

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# -- Options for notebook extension -------------------------------------------
nbsphinx_execute = "never"

# -- Options for autodoc extension -------------------------------------------
autodoc_typehints = "description"
autoclass_content = "both"

# -- Options for napoleon extension -------------------------------------------
napoleon_use_admonition_for_examples = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output


# use neo4j theme, which extends neo4j docs css for sphinx

html_theme = "sphinx_neo4j"
theme_path = pathlib.Path(__file__).parent.resolve() / "themes" / "sphinx_neo4j"


# 01-nav.js is a copy of a js file of the same name that is included in the docs-ui bundle
def setup(app):  # type: ignore
    app.add_html_theme("sphinx_neo4j", theme_path)

    app.add_js_file("https://neo4j.com/docs/assets/js/site.js", loading_method="defer")
    app.add_js_file("js/12-fragment-jumper.js", loading_method="defer")
    app.add_js_file("js/deprecated.js", loading_method="defer")


rst_epilog = """
.. |api-version| replace:: {versionnum}
""".format(
    versionnum=release,
)
