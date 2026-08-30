#!/bin/env python
'''
This script creates an SQLite3 database for Feff Data
'''
import sqlite3
import json
import lzma
from pathlib import Path

from xraydb import XrayDB, atomic_number, atomic_symbol

from .simpledb import SimpleDB
from .utils import (parse_cif, parse_feffinp, parse_feffdat,
                    get_feffdb_path)

schema = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA page_size=8192;

create table version (id integer primary key,
                      tag text not null,
                      date text not null,
                      notes text);

create table info (key text primary key not null, value text not null);

create table element (z integer primary key not null, symbol text not null,
                      name text not null, mass float not null);

create table cif (id integer primary key autoincrement,
                  ciftext blob not null,
                  space_group text not null,
                  formula text,
                  compound text,
                  source_db text,
                  source_id text);

create table feffinp (id integer primary key autoincrement,
                      absorber integer not null,
                      edge text not null,
                      scatterers text not null,
                      natoms integer not null,
                      cif_id integer,
                      inpfile blob not null,
                      foreign key(cif_id) references cif(id),
                      foreign key(absorber) references element(z) );


create table person (id integer primary key autoincrement,
                     email text not null unique,
                     name text);

insert into person (email, name) values ('feffdb@local', 'feffdb library');

create table feffdat (id integer primary key autoincrement,
                      absorber integer not null,
                      scatterer integer not null,
                      nleg integer not null,
                      reff float not null,
                      edge text not null,
                      degen integer not null,
                      geometry text not null,
                      label text,
                      description text,
                      feffinp_id integer,
                      feffdat blob not null,
                      donator_id integer default 1,
                      foreign key(feffinp_id) references feffinp(id),
                      foreign key(absorber) references element(z),
                      foreign key(scatterer) references element(z),
                      foreign key(donator_id) references person(id) );

create table rating_enum (scoreval integer primary key not null, notes text);

insert into rating_enum (scoreval) values (1);
insert into rating_enum (scoreval) values (2);
insert into rating_enum (scoreval) values (3);
insert into rating_enum (scoreval) values (4);
insert into rating_enum (scoreval) values (5);

create table feffdat_rating (id integer primary key autoincrement,
                             score integer not null,
                             review text,
                             feffdat_id integer not null,
                             person_id integer not null,
                             foreign key(score) references rating_enum(scoreval),
                             foreign key(feffdat_id) references feffdat(id),
                             foreign key(person_id) references person(id) );

"""

VERSIONS = [(1, 'beta1', '2026-August-30', 'pre-release')]

def create_feffdb(dbname=None):
    """create FeffData.DB"""
    if dbname is None:
        path = get_feffdb_path()
    else:
        path = Path(dbname)
        if path.exists():
            raise IOError(f"file {dbname} already exists")
        path.parent.mkdir(parents=True, mode=0o755, exist_ok=True)


    conn = sqlite3.connect(path)
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

def compress(val):
    return lzma.compress(val.encode('utf-8'))

def decompress(val):
    return lzma.decompress(val).decode('utf-8')


class FeffDatabase(SimpleDB):
    def __init__(self, dbname=None):
        if dbname is not None:
            path = Path(dbname)
        else:
            path = get_feffdb_path()

        self.dbname = path.absolute().as_posix()
        if not path.exists():
            create_feffdb(name=self.dbname)

        SimpleDB.__init__(self, dbname=self.dbname, server='sqlite')

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

        text = compress(out.pop('text'))
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

        text =compress(finp.pop('text'))
        fnam = finp.pop('filename')
        dbargs = {k:v for k, v in finp.items()}
        dbargs['inpfile'] = text
        dbargs['cif_id'] = cif_id

        this_id = self.__addrow('feffinp', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feffinp : {feff_inp}')
        return this_id

    def add_feffdat(self, feffdat, feff_inp, cif_file=None,
                    label=None, description=None):
        """add a Feff.dat file to the database"""

        finp_id = self.add_feffinp(feff_inp, cif_file=cif_file)

        try:
            dat = parse_feffdat(feffdat)
        except ValueError:
            raise ValueError(f'error parsing feff.dat file: {feffdat}')

        text = compress(dat.pop('text'))
        fname = dat.pop('filename')
        if description is None:
            # default description is filenamae and a few parent folders
            words = Path(fname).parts
            n = min(len(words), 4)
            description = Path(*words[-n:]).as_posix()
        if label is None:
            # default label combines absorber, scatterer, reff
            words = [atomic_symbol(dat['absorber']),
                     atomic_symbol(dat['scatterer']),
                     str(round(100*dat['reff']))]
            label = ''.join(words)
        dbargs = {k:v for k, v in dat.items()}
        dbargs['feffdat'] = text
        dbargs['feffinp_id'] = finp_id
        dbargs['label'] = label
        dbargs['description'] = description

        this_id = self.__addrow('feffdat', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feff data: {feffdat}')
        return this_id

    def get_feffdat(self, feffid):
        """get text of feff.dat, either by table 'id' or
        or by 'label' in feffdat table
        """
        try:
            where = {'id': int(feffid)}
        except ValueError:
            where = {'label': feffid}

        row = self.get_rows('feffdat', where=where,
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return decompress(row.feffdat)

    def get_feffinp(self, feffinp_id):
        "get text of feff.inp by id in feffinp table"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return decompress(row.inpfile)

    def get_feffinp_for_feffdat(self, feffdat_id):
        "get text of feff.inp for a Feff.dat file"
        row = self.get_rows('feffdat', where={'id': feffdat_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            trow = self.get_rows('feffinp', where={'id': row.feffinp_id},
                                 limit_one=True, none_if_empty=True)
            if trow is not None:
                return decompress(trow.inpfile)

    def get_cifinp_for_feffinp(self, feffinp_id):
        "get text of CIF for a feff.inp file"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            trow = self.get_rows('cif', where={'id': row.cif_id},
                                 limit_one=True, none_if_empty=True)
            if trow is not None:
                return decompress(trow.ciftext)

    def list_feffdat(self, absorber=None, scatterer=None, edge=None,
                     rmin=0., rmax=20.0):
        """get a list of feff.dat files matching on one or more criteria:

        Arguments
        ------------
        absorber   (None or str) symbol for absorber [None for all]
        scatterer  (None or str) symbol for scatterer [None for all]
        edge       (None or str) string for absorption edge [None for all]
        rmin       float  minimum R value  [0.0]
        rmax       float  maximum R value  [20.0]

        Returns
        --------
        list of path dictionaries
        """
        wargs = {}
        if absorber is not None:
            wargs['absorber'] = atomic_number(absorber.title())
        if scatterer is not None:
            wargs['scatterer'] = atomic_number(scatterer.title())
        if edge is not None:
            wargs['edge'] = edge.title()

        rows = self.get_rows('feffdat', where=wargs, limit_one=False)
        out = []
        for row in rows:
            if row.reff > rmin and row.reff < rmax:
                formula, structure = '?', '?'
                finp = self.get_rows('feffinp', where={'id': row.feffinp_id},
                                     limit_one=True, none_if_empty=True)
                if finp is not None and finp.cif_id > 0:
                    cif = self.get_rows('cif', where={'id': finp.cif_id},
                                     limit_one=True, none_if_empty=True)
                    if cif is not None:
                        formula  = cif.formula
                        compound = cif.compound.lower()

                out.append({'id': row.id,
                            'label': row.label,
                            'absorber': atomic_symbol(row.absorber),
                            'scatterer': atomic_symbol(row.scatterer),
                            'edge': row.edge,
                            'reff': row.reff,
                            'degen': row.degen,
                            'formula': formula,
                            'compound': compound,
                            'geometry': json.loads(row.geometry),
                            'description': row.description})

        return out


    def add_person(self, email, name=None):
        """add a person (email, optional name) to feffdat table:
         used for ratings and to identify added feff.dat files
        """
        dbargs = {'email': email}
        row = self.get_rows('person', where=dbargs,
                            limit_one=True, none_if_empty=True)
        if row is not None:
            if name is not None and name != row.name:
                self.update('person', where=dbargs, name=name)
            else:
                print(f"warning person {email} already exisis")
        else:
            if name is not None:
                dbargs = {'name': name}
            self.__addrow('person', dbargs)

    def get_person(self, email):
        """get person by email"""
        return self.get_rows('person', where={'email': email},
                            limit_one=True, none_if_empty=True)

    def get_feffdat_ratings(self, feffdat_id=None, email=None):
        """get all ratings for feff.dat file either by feffdat_id or by email
        """
        args = {}
        if feffdat_id is not None:
            args['feffdat_id'] = feffdat_id
        if email is not None:
            person_row = self.get_person(email)
            if person_row is not None:
                args['person_row'] = person_row.id

        return self.get_rows('feffdat_ratings', where=args)
