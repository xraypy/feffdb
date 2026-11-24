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
