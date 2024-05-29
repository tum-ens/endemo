.. Endemo documentation master file, created by
   sphinx-quickstart on Mon Jul 31 10:57:38 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Endemo's documentation!
==================================

This is the documentation for the Useful Energy Demand Model *Endemo*

How to maintain the code base
=============================

When a package import is added to the conda environment, call

.. code-block::

   >> conda env export -n <conda environment name> > endemo-env.yml

to update the file for the git repository.

When changing code in a function, always check if the docstring is still correct. Change the docstring accordingly.

How to maintain the documentation
===================================

Whenever you change something in the code and/or the doc strings, please update the documentation using

.. code-block::

   >> make html

in a command line within the docs folder!

When structural things (like package name) change, please first delete all .rst files (excluding index.rst!) and execute

.. code-block::

   >> sphinx-apidoc -o <path to docs/source> <path to endemo2 package>
   >> make html

to update this documentation properly.


.. toctree::
   :maxdepth: 10
   :caption: Contents:

   endemo2

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
