#!/bin/env python
'''
This script creates an SQLite3 database for Feff Data
'''
import sqlite3
import json
from pathlib import Path

from xraydb import XrayDB

from .simpledb import SimpleDB
from .utils import DBNAME_DEFAULT, parse_cif, parse_feffinp, parse_feffdat

schema = """
PRAGMA journal_mode=WAL;
PRAGMA page_size=8192;
create table version (id integer primary key, tag text, date text,  notes text);
create table info   (key text, value text);
create table element (z integer primary key, symbol text, name text, mass float);
create table cif (id integer primary key, ciftext text, formula text,
                  compound text, space_group text, source_db text, source_id text);
create table feffinp (id integer primary key autoincrement,
                      absorber integer, edge text, scatterers integer,
                      natoms integer, cif_id integer, inpfile text);
create table feffdat (id integer primary key autoincrement, absorber integer,
                      scatterer integer, nleg integer, reff float,
                      degen integer, geometry text, edge text,
                      feffinp_id integer, feffdat text);
"""

VERSIONS = [(1, 'alpha1', '2026-July-26', 'pre-release')]

def create_feffdb(name=DBNAME_DEFAULT):
    """create FeffData.DB"""
    if Path(name).exists():
        raise IOError(f"file {name} already exists")

    conn = sqlite3.connect(name)
    c = conn.cursor()
    for t in schema.split(';'):
        c.execute(t)

    for version_dat in VERSIONS:
        c.execute('insert into version values (?, ?, ?, ?)', version_dat)

    xdb = XrayDB()
    eltab = xdb.tables['elements']
    q = []
    for row in xdb.query(eltab).all():
        c.execute('insert into element values (?, ?, ?, ?)',
                 (row.atomic_number, row.element, row.name, row.molar_mass))
    conn.commit()


class FeffDatabase(SimpleDB):
    def __init__(self, dbname=DBNAME_DEFAULT):
        if not Path(dbname).exists():
            create_feffdb(name=dbname)

        SimpleDB.__init__(self, dbname=dbname, server='sqlite')

    def __repr__(self):
        return f"FeffDatabase('{self.dbname}')"


    def __addrow(self, table, data):
        """add row to tablle, or return existing row with data"""
        # first look if this already exists
        row = self.get_rows(table, where=data,
                            limit_one=True, none_if_empty=True)

        if row is None:
            self.insert(table, **data)
            row = self.get_rows(table, where=data,
                                limit_one=True, none_if_empty=True)
        if row is None:
            return None
        return row.id


    def add_cif_file(self, cif_file):
        """add a CIF file to the database"""
        try:
            out = parse_cif(cif_file)
        except ValueError:
            print(f"error parsing {cif_file}")
            return None

        text = out.pop('text')
        fname = out.pop('filename')
        dbargs = {k:v for k, v in out.items()}
        dbargs['ciftext'] = text
        if dbargs['source_db'] is None and fname is not None:
            dbargs['source_db'] = fname

        this_id = self.__addrow('cif', dbargs)
        if this_id is None:
            raise ValueError(f'could not add CIF: {cif_file}')
        return this_id


    def add_feffinp(self, feff_inp, cif_file=None):
        """add a Feff input file to the database"""
        cif_id = 0
        if cif_file is not None:
            cif_id = self.add_cif_file(cif_file)

        try:
            finp = parse_feffinp(feff_inp)
        except ValueError:
            raise ValueError(f'error parsing feffinp : {feff_inp}')

        text = finp.pop('text')
        fnam = finp.pop('filename')
        dbargs = {k:v for k, v in finp.items()}
        dbargs['inpfile'] = text
        dbargs['cif_id'] = cif_id

        this_id = self.__addrow('feffinp', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feffinp : {feff_inp}')
        return this_id

    def add_feffdat(self, feffdat, feff_inp, cif_file=None):
        """add a Feff.dat file to the database"""

        finp_id = self.add_feffinp(feff_inp, cif_file=cif_file)

        try:
            dat = parse_feffdat(feffdat)
        except ValueError:
            raise ValueError(f'error parsing feff.dat file: {feffdat}')

        text = dat.pop('text')
        fname = dat.pop('filename')
        dbargs = {k:v for k, v in dat.items()}
        dbargs['feffdat'] = text
        dbargs['feffinp_id'] = finp_id

        this_id = self.__addrow('feffdat', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feff data: {feffdat}')
        return this_id

    def get_feffdat(self, feffid):
        "get text of feff.dat by id in feffdat table"
        row = self.get_rows('feffdat', where={'id': feffid},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return row.feffdat

    def get_feffinp(self, feffinp_id):
        "get text of feff.inp by id in feffinp table"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return row.inpfile

    def get_feffinp_for_feffdat(self, feffdat_id):
        "get text of feff.inp for a Feff.dat file"
        row = self.get_rows('feffdat', where={'id': feffdat_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            trow = self.get_rows('feffinp', where={'id': row.feffinp_id},
                                 limit_one=True, none_if_empty=True)
            if trow is not None:
                return trow.inpfile

    def get_cifinp_for_feffinp(self, feffinp_id):
        "get text of CIF for a feff.inp file"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            trow = self.get_rows('cif', where={'id': row.cif_id},
                                 limit_one=True, none_if_empty=True)
            if trow is not None:
                return trow.ciftext

    def list_feffdat(self, absorber=None, scatterer=None, edge=None,
                     rmin=0., rmax=20.0):
        """get lit of feff.dat files matching
        absorber   (None for all)
        scatterer  (None for all)
        edge       (None for all)
        rmin       0.0
        rmax      20.0
        """
        wargs = {}
        if absorber is not None:
            wargs['absorber'] = absorber.title()
        if scatterer is not None:
            wargs['scatterer'] = scatterer.title()
        if edge is not None:
            wargs['edge'] = edge.title()

        rows = self.get_rows('feffdat', where=wargs, limit_one=False)
        out = []
        for row in rows:
            if row.reff > rmin and row.reff < rmax:
                out.append((row.id, row.absorber, row.scatterer, row.edge,
                           row.reff, row.nleg, row.degen, json.loads(row.geometry)))
        return out
