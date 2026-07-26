#!/bin/env python
'''
This script creates an SQLite3 database for Feff Data
'''
import sqlite3

from pathlib import Path

from xraydb import XrayDB

from .simpledb import SimpleDB
from .utils import DBNAME_DEFAULT, parse_cif

schema = """
PRAGMA journal_mode=WAL;
PRAGMA page_size=8192;
create table version (id integer primary key, tag text, date text,  notes text);
create table element (z integer primary key, symbol text, name text, mass float);
create table cif (id integer primary key, ciftext text, formula text,
                  compound text, source_db text, source_id text);
create table feffinp (id integer primary key autoincrement, cifid integer,
                      absorber integer, inpfile text);
create table feffdat (id integer primary key autoincrement, absorber integer,
                            scatterer integer, geometry text,
                            nleg integer, reff float, degen integer,
                            feffdat text, feffinp_id integer);
"""

VERSIONS = [(1, 'alpha1', '2026-July-22', 'pre-release')]

def create_feffdb(name=DBNAME_DEFAULT):
    """create FeffData.DB"""
    if Path(name).exists():
        raise IOError(f"file {name} already exists")

    conn = sqlite3.connect(name)

    c = conn.cursor()
    for t in schema.split(';'):
        print(t)
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

    def add_ciffile(self, ciffile):
        parse_cif(ciffile)


feffdb = FeffDatabase()
print(feffdb)
print(feffdb.tables.keys())

dat = feffdb.add_ciffile('../fayalite.cif')
print(dat.keys())
