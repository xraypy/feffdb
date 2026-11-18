.. include:: _config.rst

.. _contributing:

Contributing to FeffDB
===============================================

While `feffdb` contains several hundred EXAFS Paths for dozens of absorbing
atoms, it is far from complete.  We hope users will contribute novel paths relevant to their own projects for the benefit of the XAFS community. Currently, we ask that those who wish to contribute provide the same files that we include in the database - i.e., the CIF, FEFF input file, and FEFFXXXX.dat paths for a given bond type. 
The FEFF input file will be fed through a parser to extract the FEFF settings (SCF, cluster radius, exchange potential, and version.) The contributed can then be adjusted to be consistent with the rest of the database - since users can regenerate the database from scratch, they can also select the FEFF version that best serves their purposes. For example, though the original database was done in FEFF8.5L, a user may want to use its paths for their project done in FEFF6. The FEFF_version_converter.py script will translate between FEFF versions. Users can then rerun the calculations in the appropriate version. 

FeffDB contributions will be reviewed by an automatic algorithm to check for corrupt, empty, or irrelevant files as well as completeness. If these properties are found to be satisfactory, the algorithm will add these contributions to the database periodically (ideally every couple hours), such that the github repo reflects the most recent version of the database.
