.. include:: _config.rst

Installation
=====================

As an SQLite3 database, the latest version of FeffDB is available
`feffdat.db`_.  See :ref:`database` for description of the SQLite3
schema used.  At this writing, the version of the database is `0.9.0`,
marked as "pre-release".

Currently, programming suport with FeffDB is provided only for Python.
If you are using it from another language, contact the project
maintainers.


Python Prerequisites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The current version of FeffDB Python package is |release|. This is a
pre-release version, last updated in November, 2026.  It requires
Python 3.11 or higher.  The FeffDB code is pure Python, with required
packages and minimum versions listed in the `pyproject.toml` file in
the source code repository.  The required packages are all readily
available from PyPI or on `conda` channels such as `conda-forge`.

While the FeffDB Python project is closely associated with the
xraylarch suite and package, xraylarch is not a dependency for FeffDB.


Installation with pip
~~~~~~~~~~~~~~~~~~~~~~~~~~

The latest version (|release|) is available from `PyPI`_ and can be
installed with::

   pip install feffdb


Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

The development version can be cloned with::

   git clone https://github.com/xraypy/feffdb.git


You can then move into this repository, and install the development version with::

   cd feffdb
   python -m pip install .

Installed Scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On install, 2 execuatable scripts will be installed in your Python
environment:

   1. :ref:`feffdb_cli`.  This utility allows you can browse and list
      Feff Paths from the FeffDB.
   2. :ref:`feffinp_convert_cli`.  This utility allows you to convert
      Feff.inp files to work with different versions of Feff.


License
~~~~~~~~~~~~~

The source code and documentation for FeffDB are distributed under the following license:

..  literalinclude:: ../LICENSE
