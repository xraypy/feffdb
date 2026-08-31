.. include:: _config.rst

Installation
=====================


Prerequisites
~~~~~~~~~~~~~~~

The current version of FeffDB is |release|. This is a pre-release
version, last updated in August, 2026.

FeffDB requires Python 3.11 or higher and wxPython 4.2.4.  Other
required packages and minimum versions are listed in the
`pyproject.toml` file in the source code repository.  All of the
required dependencies are available from `pip` or on `conda` channels.

Installation with pip
~~~~~~~~~~~~~~~~~~~~~~~~~~

The latest version (|release|) is available from `PyPI`_ and can be
installed with::

   pip install fefdb


Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

The development version can be cloned with::

   git clone https://github.com/xraypy/feffdb.git

Installation from Source
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FeffDB is a pure python module, so installation on all platforms can use
the source kit and a standard installation using::

   python -m pip install .


.. _desktop_shortcut:

License
~~~~~~~~~~~~~

The source code and documentation for Sitka Source are distributed under the following license:

..  literalinclude:: ../LICENSE
