This is a passion project that grew from several scripts I used to help me grade college C-language programming assignments.
I still need to clean up several things from the times I 'just needed something to do X 10 days ago'.
If you find this software helpful, please let me know!

========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - |github-actions| |codecov|
    * - package
      - |version| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/python-agh/badge/?style=flat
    :target: https://readthedocs.org/projects/python-agh/
    :alt: Documentation Status

.. |github-actions| image:: https://github.com/Tuck-Williamson/python-agh/actions/workflows/github-actions.yml/badge.svg
    :alt: GitHub Actions Build Status
    :target: https://github.com/Tuck-Williamson/python-agh/actions

.. |codecov| image:: https://codecov.io/gh/Tuck-Williamson/python-agh/branch/main/graphs/badge.svg?branch=main
    :alt: Coverage Status
    :target: https://app.codecov.io/github/Tuck-Williamson/python-agh

.. |version| image:: https://img.shields.io/pypi/v/agh.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/agh

.. |wheel| image:: https://img.shields.io/pypi/wheel/agh.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/agh

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/agh.svg
    :alt: Supported versions
    :target: https://pypi.org/project/agh

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/agh.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/agh




.. end-badges

An assignment grading helper

* Free software: GNU Lesser General Public License v3 or later (LGPLv3+)
* Based off of https://github.com/ionelmc/cookiecutter-pylibrary.

Installation
============

::

    pip install agh

You can also install the in-development version with::

    pip install https://github.com/Tuck-Williamson/python-agh/archive/main.zip


Documentation
=============


https://python-agh.readthedocs.io/


Development
===========

To run all the tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
