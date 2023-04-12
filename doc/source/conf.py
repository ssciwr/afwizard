# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import subprocess
import sys

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath("../.."))

# Install the afwizard package - this is a horrible but necessary to work around
# a Conda/Pip compatibility issue on RTD: We can only provide either a conda env
# OR a pip requirements file. From the pip section of the env file, we cannot
# specify the --no-deps flag, but without this the pip install of afwizard
# corrupts the conda environment. See e.g. https://github.com/conda/conda/issues/6805
if os.environ.get("READTHEDOCS", None) == "True":
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "../.."])

import afwizard

# -- Project information -----------------------------------------------------

project = "Adaptive Filtering Wizard"
copyright = "2021, Scientific Software Center, Heidelberg University"
author = "Dominic Kempf"

# The full version, including alpha/beta/rc tags
release = afwizard.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "m2r2",
    "sphinx_rtd_theme",
    "nbsphinx",
    "nbsphinx_link",
    "sphinx_click",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Make sure that classes are documented by their init method
autoclass_content = "init"

# This is an extension that allows us to preserve the default arguments of functions
# as written in code without evaluating them.
autodoc_preserve_defaults = True

# This is kind of unfortunate, but we get errors that are specific to the documentation build:
nbsphinx_allow_errors = True

# Modify the width of the layout. Taken from:
# https://stackoverflow.com/a/43186995/2819459
def setup(app):
    app.add_css_file("style.css")


# Ensure that the conda provided PROJ database is found. This
# is somewhat not possible in the base environment. There is
# this discussion which allowed me to solve the issue although I
# think it is a horrible situation and definitely a bug:
# https://github.com/conda-forge/geopandas-feedstock/issues/63
if os.environ.get("READTHEDOCS", None) == "True":
    os.environ[
        "PROJ_LIB"
    ] = "/home/docs/checkouts/readthedocs.org/user_builds/afwizard/conda/nakadake-data/share/proj"
