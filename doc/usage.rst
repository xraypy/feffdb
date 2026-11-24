.. include:: _config.rst


.. _usage:

Python Usage
============================================

The `feffdb` Python module allows users to look up and extract Feff
paths, and their associated Feff input and CIF files.  Basic EXAFS
calculations of :math:`\chi(k)` using the Feff Paths are also
supported, though more comprehensive tools for working with the Feff
Paths are available in `xraylarch`_.  Users can also add Feff Paths to
their local copy of the database for later use.  To do this,


In contribute these
for inclusion

calculations are
well established and relatively fast to run, and a myriad of CIFs can
be found through both computational and experimental databases such as
the Materials Project or the ICSD, respectively. However, the curation
of these files together is still quite useful for experienced and
beginning users alike as the selection criteria used to select
structures (such as not allowing partial occupancy) allow one to sort
through a heavily abbreviated set of options for path fitting. The
path fits will likely not start completely correct, but can be refined
to produce fits with neater statistical "closeness of fit" parameters
and physical plausibility, among other factors.

.. _dblocation:

Database location
~~~~~~~~~~~~~~~~~~~~~~~~

On installation, the version of the SQLite3 database distributed with
the Python package (`feffdat.db`_), is installed into the folder with
the Python code.  This folder may not be writeable by all users, for
example if it had been installed with elevated privileges or into a
system-with Python environment.  Users may want to add Feff Paths and
maintain a personal copy of FeffDB that survives reinstallation of the
Python package and can be used from multiple Python environments.


To accomodate having a user-specific FeffDB database, the Python
package will look in a user-specific folder for a valid FeffDB
database. This location depends on operation system, being

  +--------------------+-----------------------------------------------------------------+
  |  Operating System  |  default FeffDB location                                        |
  +====================+=================================================================+
  |  Windows           |  C:\Users\<UserName>\AppData\Local\feffdb\feffdb\feffdat.db     |
  +--------------------+-----------------------------------------------------------------+
  |  macOS             | /Users/<UserName>/Library/Application Support/feffdb/feffdat.db |
  +--------------------+-----------------------------------------------------------------+
  |  Linux             | /home/<UserName>/.local/feffdb/feffdat.db                       |
  +--------------------+-----------------------------------------------------------------+

By default, if this file is not found, the Python library will try to
copy it from the installed Python source directory.  If this cannot be
copied, the library will fall back to using the as-installed version.

You can specify using a different FeffDB database in two ways:

    1. setting the environmental variable FEFFDB_FILE
    2. explicitly setting the value of `dbname` to either the `feffdb`
       CLI or when creating the FeffDatabase object.

In both cases, the argument should be the full path to the FEFFDB
file.  To recap, the order for deciding which FEFFDB to use are:

    1. if explicity given, and that path exists, it is used.
    2. if FEFFDB_FILE environment variable is set, and that path exists, it is used.
    3. if the 'user-installed FEFFDB file` from the table above exists, it is used.
    4. if the 'user-installed FEFFDB file` does not exist, the
       installed FEFFDB is attempted to be copied to that location.
    5. finally, the installed FEFFDB is used.

`FeffDatabase`
~~~~~~~~~~~~~~~~~~~~~~~~


The main interface to `feffdb` is the :class:`FeffDatabase` class,
which can be used with:

    >>> from feffdb import FeffDatabase
    >>> fdb = FeffDatabase()
    >>> print(fdb)
    FeffDatabase('/Users/UserName/Library/Application Support/feffdb/feffdat.db') dbversion=0.9.0
    >>> for znpath in fdb.list_feffdat(absorber='Zn', scatterer='O'):
    ...     print(znpath['label'], znpath['reff'], znpath['edge'], znpath['formula')
    ZnO211 2.1105 K ZnCO3
    ZnO197 1.9738 K ZnO
    ZnO193 1.9335 K Zn3As2O6
    ...
    >>> feffdat_ZnO197 = fdb.get_feffdat('ZnO197')

Here, `feffdat_ZnO211' will be the text of the Feff Datafile for that
path.
