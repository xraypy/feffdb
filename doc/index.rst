.. feffdb spruce documentation index file

.. include:: _config.rst


========================================================
FeffDB: A database of EXAFS calculations
========================================================

FeffDB is an `SQLite3`_ database storing selected EXAFS calculations
from the `Feff`_ program, and a Python library to read, write, and
work with this database and the data it contains.  In principe, the
database can be retrieved from languages other than Python, but there
is not currently any library to work with the database.

The main motivation for Feff DB is to provide "first-shell EXAFS"
calculations for many common ligands or atom pairs that these can be
browsed and re-used without having to setup and run Feff. An important
use-case for this is semi-automated analysis of EXAFS data.

FeffDB is still in active, pre-release development, and has been
developed by;

  - Samantha Liao, Cornell University,   https://orcid.org/0009-0006-7803-4106
  - Juanjuan Huang, Argonne National Laboratory, https://orcid.org/0000-0002-5801-9754
  - Nina Andrejevic, Argonne National Laboratory, https://orcid.org/0000-0002-8648-5859
  - Yanna Chen, Canadian Light Source, https://orcid.org/0000-0001-7937-4395
  - Matthew Newville, The University of Chicago, https://orcid.org/0000-0001-6938-1014
  - Shelly Kelly, Argonne National Laboratory, https://orcid.org/0000-0001-8996-628X




:bdg-link-info:`GitHub <https://github.com/xraypy/feffdb>`
:bdg-link-info:`PyPI <https://pypi.org/project/feffdb/>`


.. toctree::
   :maxdepth: 2

   install
   motivation
