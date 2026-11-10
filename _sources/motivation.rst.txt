.. include:: _config.rst

.. _motivation:

Motivation
===============================

`Feff`_ is a collection of programs for calculating X-ray absorption
and related spectroscopies.  The code and research that went into the
physical insight for these calculations originated with the work of
`John Rehr`_ and his research group.  The work here focuses on some
of the earliest codes from Rehr's group to calculate EXAFS
contrubutions for selected photoelectron scattering paths for an
absorber and scatterer pair.  In fact, the emphasis is on fist-shell
scattering, or near-neighbor paths which usually dominate the EXAFS
scattering and can be used in a semi-automated way.


Feff calclulates EXAFS for each *scattering path* taken by the
photo-electron. While setting up a calculation is not too difficult,
and running the Feff program to do the calculation is not too slow, it
is still some work, and it is possible to make some bad (or even
"wrong") choices, and end up with a problematic result.  Using the
calculation results is also not too difficult, but not exactly
trivial.  Still, in the most general case, a calculation needs to be
done.

To do the Feff calculation, you need to have a cluster of atoms, and
identify the absorbing atom and X-ray edge.  The atomic cluster does
not need to be too big, or generated from a crystal structure, but
this is an easy way to start, and the expectation for the calculations here.

FeffDB is a collection of Feff EXAFS calculations -- effectively, the
``feff0001.dat`` (and maybe ``feff0002.dat``) files for the first
neighbor from running Feff (all the results are currently from
Feff8L).  When possible (and for all current examples), the content of
the ``feff.inp`` file used for the calculation, and the CIF file used
to generate that ``feff.inp`` file are also included in the database.

The data are stored in a single file (typically called `feffdat.db`)
that is an SQLite3 database.  This stores data in a number of Tables,
with columns of fixed name and intended meaning, but many rows, one
for each entry.
