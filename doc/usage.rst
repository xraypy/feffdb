.. include:: _config.rst

.. _feffdb_cli:

`feffdb` CLI
==================

On installation of the Python pacakge, a `feffdb` command-line utility
will be installed.  This will allow you to browse the Paths available
in the database.  Usage notes are::


    usage: feffdb [-h] [-n DBNAME] [-c] [-v] [--rmin RMIN] [--rmax RMAX] [absorber] [scatterer]

    Feff Database Utility

    positional arguments:
      absorber           symbol for absorbing element (use "all" for all absorbers)
      scatterer          symbol for scattering element

    options:
      -h, --help         show this help message and exit
      -n, --name DBNAME  database to use [<default location of feffdat.db>]
      -c, --create       create new database if it does not exist
      -v, --version      print version information
      --rmin RMIN        minimum distance (Ang)
      --rmax RMAX        maximum distance (Ang)

An example usage to list available Cu-O Paths would be::

   ~> feffdb Cu O

which would print out a table like this


  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |   id | label   | absorber   | scatterer   | edge   |   reff |   degen | formula     | compound     | description                          |
  +======+=========+============+=============+========+========+=========+=============+==============+======================================+
  |   11 | CuO195  | Cu         | O           | K      | 1.9472 |       2 | CuO         | tenorite     | Cu1_K_Tenorite_cif11639/feff0001.dat |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  250 | CuO230  | Cu         | O           | K      | 2.3025 |       6 | PbCu6O8     | murdochite   | AMCSD_76_R2.30/feff0001.dat          |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  251 | CuO216  | Cu         | O           | K      | 2.1558 |       6 | PbCu6O8     | murdochite   | AMCSD_9908_R2.16/feff0001.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  252 | CuO203  | Cu         | O           | K      | 2.0264 |       4 | VCuLiO4     | <missing>    | AMCSD_12263_R2.13/feff0001.dat       |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  253 | CuO219  | Cu         | O           | K      | 2.1875 |       2 | VCuLiO4     | <missing>    | AMCSD_12263_R2.13/feff0002.dat       |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  254 | CuO185  | Cu         | O           | K      | 1.8488 |       2 | Cu2O        | cuprite      | AMCSD_7351_R1.85/feff0001.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  255 | CuO200  | Cu         | O           | K      | 1.9952 |       2 | Cu2Cl(O3H3) | atacamite    | AMCSD_9136_R2.01/feff0001.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  256 | CuO209  | Cu         | O           | K      | 2.0886 |       1 | CaCuAsO5H   | conichalcite | AMCSD_5080_R2.02/feff0003.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  257 | CuO228  | Cu         | O           | K      | 2.2845 |       1 | CaCuAsO5H   | conichalcite | AMCSD_5080_R2.02/feff0004.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+
  |  258 | CuO238  | Cu         | O           | K      | 2.3797 |       1 | CaCuAsO5H   | conichalcite | AMCSD_5080_R2.02/feff0005.dat        |
  +------+---------+------------+-------------+--------+--------+---------+-------------+--------------+--------------------------------------+




.. _usage:

Python usage
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
