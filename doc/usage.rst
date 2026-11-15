.. include:: _config.rst

.. _usage:

Usage from Python
============================================

The  `feffdb` Python module allows a user to look up CIFs and FEFF paths directly
as well as contribute to the db. FEFF calculations are well established and relatively fast to run, and a myriad of CIFs can be found through both computational and experimental databases such as the Materials Project or the ICSD, respectively. However, the curation of these files together is still quite useful for experienced and beginning users alike as the selection criteria used to select structures (such as not allowing partial occupancy) allow one to sort through a heavily abbreviated set of options for path fitting. The path fits will likely not start completely correct, but can be refined to produce fits with neater statistical "closeness of fit" parameters and physical plausibility, among other factors. 

