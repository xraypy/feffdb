.. feffdb spruce documentation index file

.. include:: _config.rst


========================================================
FeffDB: A database of EXAFS calculations
========================================================

FeffDB is an `SQLite3`_ database storing selected EXAFS calculations
from the `Feff`_ program, and a Python library to read, write, and
work with this database.  The motivation for Feff DB is to provide
"first-shell EXAFS" calculations for many common ligands or atom pairs
that these can be browsed and re-used without having to setup and run
Feff. An important use-case for this is semi-automated analysis of
EXAFS data.

FeffDB is still in active, pre-release development. It is being
developed by

  - Samantha Liao, Cornell University,   https://orcid.org/0009-0006-7803-4106
  - Juanjuan Huang, Argonne National Laboratory, https://orcid.org/0000-0002-5801-9754
  - Nina Andrejevic, Argonne National Laboratory, https://orcid.org/0000-0002-8648-5859
  - Yanna Chen, Canadian Light Source, https://orcid.org/0000-0001-7937-4395
  - Matthew Newville, The University of Chicago, https://orcid.org/0000-0001-6938-1014
  - Shelly Kelly, Argonne National Laboratory, https://orcid.org/0000-0001-8996-628X

In principe, the database could be used from languages other than
Python. This is not currently supported here, but we welcome
discussion of that possibility.


A note on the name: We mean "FeffDB" to mean "The database (DB) of
EXAFS calculations that come from the program Feff".  But "FEFFDB"
also turns out to be a triple of hexidecimal numbers ((254, 255, 219)
in decimal), which means "FEFFDB" can be used as a color, bright
yellow. In the X11 color scheme, the closest color is "Corn Silk".
According to https://colorkit.co/color/feffdb/, it can be called
"Parmesan", and https://www.schemecolor.com/hex/feffdb calls it "Moon
Glow".  We like all of these names as synonyms for FeffDB.



:bdg-link-info:`GitHub <https://github.com/xraypy/feffdb>`
:bdg-link-info:`PyPI <https://pypi.org/project/feffdb/>`


.. toctree::
   :maxdepth: 2

   install
   usage
   motivation
   contrib
   dbschema
