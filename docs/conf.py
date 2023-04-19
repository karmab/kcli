# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('..'))
# sys.setrecursionlimit(1500)

# import pdoc
# from typing import Sequence
#
#
# def _flatten_submodules(modules: Sequence[pdoc.Module]):
#    for module in modules:
#        yield module
#        for submodule in module.submodules():
#            yield from _flatten_submodules((submodule,))
#
#
# context = pdoc.Context()
# module = pdoc.Module('kvirt', context=context)
# modules = list(_flatten_submodules([module]))
#
# with open('docs/index.md', 'a+') as d:
#    d.write(pdoc._render_template('/pdf.mako', modules=modules))


# -- Project information -----------------------------------------------------

project = 'Kcli'
copyright = '2020, karmab'
author = 'karmab'

# The full version, including alpha/beta/rc tags
release = '99.0'

master_doc = 'index'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
# extensions = ['autoapi.extension']
# extensions = ['sphinx.ext.autodoc', 'autoapi.extension', 'sphinx_rtd_theme', 'sphinx.ext.napoleon']
# extensions = ['autoapi.extension', 'sphinx_rtd_theme', 'sphinx.ext.napoleon']
# extensions = ['sphinx_rtd_theme', 'sphinx.ext.napoleon']
extensions = ['sphinx_rtd_theme']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# a list of builtin themes.
#
html_theme = 'pydata_sphinx_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
