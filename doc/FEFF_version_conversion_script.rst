=========================================
Converting between Feff versions
=========================================

This script is to allow users who are working in one Feff version to regenerate the database in another Feff version. The covered Feff versions are FEFF6L, FEFF8.5L, FEFF9, and FEFF10.
The script lives in ``feff_version_converter_script/feff_convert.py`` and will only rewrite FEFF input files rather than running FEFF itself, which requires a license for FEFF9 and FEFF10. 
The script itself was written by Claude but a human checked that it gave the expected outputs.

  

A worked example (fcc Cu, Feff8.5L --> Feff6L)
-----------------------------------------------
To run feff_convert.py, enter the following into the command line::

    python3 feff_version_converter_script/feff_convert.py \
        feff_version_converter_script/tests/inputs/cu_fcc_feff85l.inp \
        --to feff6 -o cu_fcc_converted.inp

Two warnings will be printed *due to FEFF8.5L having more settings than FEFF6L.*::

    WARNING: CONTROL: mfms dropped; FEFF6 has no FMS module
    WARNING: PRINT: ff2x level 3 clamped to 2; FEFF6 ff2chi only
    defines 0, 1 and 2, and writes feffNNNN.dat from genfmt

These are expected. The ``CONTROL`` and ``PRINT`` cards hold four
flags in Feff6 and six in Feff8, and the flags do not line up, so a
card copied across unchanged would quietly mean something else. The
converted file reads::

    HOLE 1 1.0
    CONTROL 1 1 1 1
    PRINT 1 0 1 2

``EDGE K`` became ``HOLE 1 1.0`` because Feff6 names the core hole by
index rather than by edge label.

Options
----------------------
``--to``
    Required. One of ``feff6``, ``feff85l``, ``feff8``, ``feff9``,
    ``feff10``. The Feff6 and Feff8.5L mappings were checked against
    the feff85exafs source and against real runs; the others are
    unverified.
``-o``
    Output path. Defaults to ``feff_converted.inp``.

``--mode``
    ``compatible`` (default) keeps the calculation Feff6-like, so the
    two versions stay comparable. ``native`` keeps ``SCF``, ``FMS``
    and ``XANES`` and lets the newer version use its own physics.

``--run``
    Also runs the target executable, if one is on your PATH.


A note on S02
----------------------
S02 doesn't transfer between FEFF versions, so it must be refit after converting.



