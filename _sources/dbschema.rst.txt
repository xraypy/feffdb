.. include:: _config.rst

.. _database:

The FeffDB Database
============================================

`feffdb` is primarily an `SQLite3`_ database.  The schema
is given in
https://github.com/xraypy/feffdb/blob/main/feffdb/schema.py.
The initial SQL code shown there:

    PRAGMA journal_mode=WAL;
    PRAGMA foreign_keys=ON;
    PRAGMA page_size=8192;

first sets the database to be in "WAL" (or "Write-Ahead-Log") mode.
This can greatly improve database performance, though it is less
important when opened in "read only" mode.   Then SQLite is told to
support "foreign keys", and the "page size" for a single block of data
are set.  We find that all of these can improve performance.

The tables used the database are then given.  These tables can all be
thought of as tables in a Spreadsheet, where the Columns have (more or
less) predefined meaning and datatypes, and each Row in the Table
would be a different data entry.  One main differences between a
Spreadsheet and a database are that the data in any one Column could
be very large in a database.  Another main difference is that a Column
in one Table could be or "point to" the Column Index in another Table,
and the SQL language makes it easy and efficient to get data from
multiple tables that are related with these "pointing Columns" --
these are the "relation" that make it a "relational database".

We'll descibe the Column names, data types and intended meaning for
the main Tables in the Feff DB


.. index:: Version Table
.. _db_version_table:

   DB Table of Database Versions: this table holds version information
   for the database, which can allow the database to evolve and
   support backward compatibility.

    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  tag                 |  text        | version name                          |
    +----------------------+--------------+---------------------------------------+
    |  date                |  text        | date string                           |
    +----------------------+--------------+---------------------------------------+
    |  notes               |  text        | notes on changes for version          |
    +----------------------+--------------+---------------------------------------+

.. index:: Info Table
.. _db_info_table:

   DB Table of Info: A simple table that can be used for ancillary data.


    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  key                 |  text        | name for value                        |
    +----------------------+--------------+---------------------------------------+
    |  value               |  text        | value                                 |
    +----------------------+--------------+---------------------------------------+

.. index:: CIF Table
.. _db_cif_table:

   DB Table of CIF Data: A table of data from CIF crystallographic files


    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  ciftext             |  text        | compressed text of the CIF file       |
    +----------------------+--------------+---------------------------------------+
    |  space_group         |  text        | Space Group (H-M notation)            |
    +----------------------+--------------+---------------------------------------+
    |  formula             |  text        | chemical formula                      |
    +----------------------+--------------+---------------------------------------+
    |  compound            |  text        | name of compound, mineral             |
    +----------------------+--------------+---------------------------------------+
    |  source_db           |  text        | name of source DB for this CIF        |
    +----------------------+--------------+---------------------------------------+
    |  source_id           |  text        | index within source DB                |
    +----------------------+--------------+---------------------------------------+


.. index:: Feff.inp Table
.. _db_feffinp_table:

   DB Table of Feff Input file Data.


    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  inptext             |  text        | compressed text of the Feff.inp file  |
    +----------------------+--------------+---------------------------------------+
    |  absorber            |  integer     | Atomic number of absorbing element    |
    +----------------------+--------------+---------------------------------------+
    |  edge                |  text        | absorbin edge (K, L3, ...)            |
    +----------------------+--------------+---------------------------------------+
    |  scatterers          |  text        | JSON-encoded list of scattering atoms |
    +----------------------+--------------+---------------------------------------+
    |  natoms              |  integer     | number of atoms in cluster            |
    +----------------------+--------------+---------------------------------------+
    |  cif_id              |  integer     | CIF table id used to create inptext   |
    +----------------------+--------------+---------------------------------------+

.. index:: Feff.dat Table
.. _db_feffdat_table:

   DB Table of Feff Data files, supporting single-scattering Feff data files

    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  absorber            |  integer     | Atomic number of absorbing element    |
    +----------------------+--------------+---------------------------------------+
    |  scatterer           |  integer     | Atomic number of scattering element   |
    +----------------------+--------------+---------------------------------------+
    |  edge                |  text        | absorbin edge (K, L3, ...)            |
    +----------------------+--------------+---------------------------------------+
    |  reff                |  float       | distance between atoms                |
    +----------------------+--------------+---------------------------------------+
    |  nleg                |  integer     | number of Path legs (==2)             |
    +----------------------+--------------+---------------------------------------+
    |  degen               |  integer     | number of equivalent paths            |
    +----------------------+--------------+---------------------------------------+
    |  geometry            |  text        | JSON-encoded Path geometry            |
    +----------------------+--------------+---------------------------------------+
    |  label               |  text        | short, unique label path              |
    +----------------------+--------------+---------------------------------------+
    |  description         |  text        | usually Path of original Feff file    |
    +----------------------+--------------+---------------------------------------+
    |  feffdat             |  text        | compressed text of the Feff.dat file  |
    +----------------------+--------------+---------------------------------------+
    |  feffinp_id          |  integer     | FEFFINP table id used to create data  |
    +----------------------+--------------+---------------------------------------+
    |  donator_id          |  integer     | PERSON table id for donator           |
    +----------------------+--------------+---------------------------------------+


.. index:: Person Table
.. _db_person_table:

   DB Table of People, ussd to identify donators and reviewers


    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  email               |  text        | email address                         |
    +----------------------+--------------+---------------------------------------+
    |  name                |  text        | full name                             |
    +----------------------+--------------+---------------------------------------+
    |  password            |  text        | hashed password                       |
    +----------------------+--------------+---------------------------------------+


.. index:: Ratings Table
.. _db_ratings_table:

   DB Table of Ratings and reviews of Feff data files


    +----------------------+--------------+---------------------------------------+
    |  Column              |  Type        | Description                           |
    +======================+==============+=======================================+
    |  id                  |  integer     | counter (primary tag)                 |
    +----------------------+--------------+---------------------------------------+
    |  score               |  integer     | score: 1 (worst) to 5 (best)          |
    +----------------------+--------------+---------------------------------------+
    |  review              |  text        | text of review                        |
    +----------------------+--------------+---------------------------------------+
    |  feffdat_id          |  integer     | FEFFDAT table id for PAth reviewed    |
    +----------------------+--------------+---------------------------------------+
    |  person_id           |  integer     | PERSON table id for reviewer          |
    +----------------------+--------------+---------------------------------------+
