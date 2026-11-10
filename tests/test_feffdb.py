"""
testing for FeffDB
"""
import json
import lzma
import pytest
import numpy as np
from numpy.testing import assert_allclose

import subprocess

from feffdb import get_feffdb, FeffDatabase
from feffdb.feffdb import decompress

def test_get_feffdb():
    dbpath = get_feffdb()
    assert dbpath is not None
    assert dbpath.exists()
    assert dbpath.name == 'feffdat.db'

def test_init_feffdb():
    dbpath = get_feffdb()
    fdb = FeffDatabase()

    assert dbpath.as_posix() == fdb.dbname

    tablenames = list(fdb.tables.keys())
    for tname in ('cif', 'element', 'feffinp',
                  'feffdat', 'info', 'version'):
        assert tname  in tablenames

def test_cif_table():
    fdb = FeffDatabase()
    cif_rows = fdb.get_rows('cif')
    assert len(cif_rows) > 200

    for i in range(10, 200, 10):
        crow = cif_rows[i]
        fname = crow._fields
        for cif_col in ('id', 'ciftext', 'space_group', 'formula',
                        'compound', 'source_db', 'source_id'):
            assert cif_col in crow._fields
        assert crow.id > 0
        assert len(crow.space_group) > 0
        assert len(crow.ciftext) > 0

        text_a = decompress(crow.ciftext)
        text_b = lzma.decompress(crow.ciftext).decode('utf-8')

        assert text_a == text_b

        for cif_key in ('data_global', 'loop_', '_journal',
                        '_database_code_amcsd',
                        '_cell_length_a', '_cell_angle_beta',
                        '_symmetry_space_group'):
            assert cif_key in text_a

def test_feffdb_table():
    fdb = FeffDatabase()
    fdrows = fdb.get_rows('feffdat')
    assert len(fdrows) > 300
    for i in range(3, 300, 5):
        fdrow = fdrows[i]
        fname = fdrow._fields
        for fd_col in ('id', 'absorber', 'scatterer', 'nleg', 'reff',
                       'edge', 'degen', 'geometry', 'label', 'description',
                       'feffinp_id', 'feffdat', 'donator_id'):
            assert fd_col in fdrow._fields
        assert fdrow.id > 0
        assert isinstance(fdrow.absorber, int)
        assert fdrow.absorber > 0
        assert fdrow.absorber < 150
        assert isinstance(fdrow.scatterer, int)
        assert fdrow.scatterer > 0
        assert fdrow.scatterer < 150
        assert isinstance(fdrow.nleg, int)
        assert fdrow.nleg == 2
        assert isinstance(fdrow.reff, float)
        assert fdrow.reff > 0.5
        assert fdrow.reff < 6.5
        assert fdrow.edge in ('K', 'L3', 'L2')
        assert isinstance(fdrow.feffinp_id, int)
        assert fdrow.feffinp_id > 0
        assert fdrow.feffinp_id < 5000

        assert len(fdrow.feffdat) > 50

        text_a = decompress(fdrow.feffdat)
        text_b = lzma.decompress(fdrow.feffdat).decode('utf-8')

        assert text_a == text_b
        assert len(text_a) >  4000
        assert len(text_a) < 14000

        for feffd_key in ('POT', 'Abs', 'Pot', 'Gam_ch', 'Rs_int',
                          'PATH', 'reff', 'absorbing'):
            assert feffd_key in text_a


def test_feffdb_app():
    text  = subprocess.check_output(['feffdb', 'Ni']).decode('utf-8')
    lines = text.split('\n')
    assert len(lines) > 22
    assert len(lines) < 400
    for word in ('NiO208', 'liebenbergite', 'Ni1_K_Nickel_cif11153'):
        assert word in text
