#!/bin/env python
'''
This script creates an SQLite3 database for Feff Data
'''
import json
from pathlib import Path
from pyshortcuts import hash_password, check_password_rules
from xraydb import atomic_number, atomic_symbol

from .simpledb import SimpleDB
from .utils import (get_feffdb, create_feffdb, read_textfile,
                    parse_cif, parse_feffinp, parse_feffdat,
                    compress, decompress)

class FeffDatabase(SimpleDB):
    """
    create a FeffDB Database instance

    Parameters
    -----------
    dbname: str or None
      filename or Path to database file [None]
    create_ok : bool
      whether it is OK to create a new FeffDB [False]
    read_only : bool
      whether to try to open FeffDB as read-only [False]

    Returns
    --------
    FeffDatabase instance

    Notes
    ------
    1. if `dbname` is `None`, it will be found with the `get_feffdb` function.

    """
    def __init__(self, dbname=None, create_ok=False, read_only=False):
        if dbname is not None:
           dbpath = Path(dbname)
        else:
            try:
                dbpath = get_feffdb()
            except ValueError:
                dbpath = None

        if (dbpath is None or not dbpath.exists()) and create_ok:
            create_feffdb(dbname=dbname)

        self.dbname = dbpath.absolute().as_posix()
        SimpleDB.__init__(self, dbname=self.dbname, server='sqlite',
                          read_only=read_only)
        self.get_version()
        if self.dbversion_full['id'] < 2:
            raise ValueError('FeffDB version beta1 not supported, please upgrade FeffDB')

    def __repr__(self):
        return f"FeffDatabase('{self.dbname}') dbversion={self.dbversion}"


    def __addrow(self, table, data):
        """add row to table or return existing row with data

        Parameters
        -----------
        table:  str
           name of table
        data: dict
           dict of data for row

        Returns
        -------
        integer id of added or existing row or None if not added.
        """
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

    def get_version(self):
        """get version information

        Returns
        ---------
        dict with version information

        Notes
        -----
        sets `.dbversion` and `.dbversion_full` attributes
        """
        vrows = self.get_rows('version')
        self.dbversion_full = vrows[-1]._asdict()
        self.dbversion = self.dbversion_full['tag']
        return self.dbversion_full

    def add_cif_file(self, cif_file):
        """add a CIF file to the database

        Parameters
        ---------
        cif_file : str or Path
           name or Path of CIF file
        """
        try:
            out = parse_cif(cif_file)
        except ValueError:
            print(f"error parsing {cif_file}")
            return None

        text = compress(out.pop('text'))
        fname = out.pop('filename')
        dbargs = {k:v for k, v in out.items()}
        dbargs['text'] = text
        if dbargs['source_db'] is None and fname is not None:
            dbargs['source_db'] = fname

        this_id = self.__addrow('cif', dbargs)
        if this_id is None:
            raise ValueError(f'could not add CIF: {cif_file}')
        return this_id

    def add_cluster_file(self, cluster_file, format='xyz',
                         formula='unknown', compound='unknown',
                         notes=''):
        """add a cluster file (say, XYZ) to the database

        Parameters
        ---------
        cluster_file: str or Path
           name or Path of cluster file
        format:  str
           cluster format/type ['xyz']
        formula: str
           chemical formula ['unknown']
        compound: str
           compound name ['unknown']
        notes: str
           cluster notes ['']
        """

        try:
            out = read_textfile(cluster_file)
        except ValueError:
            print(f"error reading {cluster_file}")
            return None

        text = compress(out)
        source = cluster_file
        dbargs = {'text': text, 'source': cluster_file,
                  'format': format, 'formula': formula,
                  'compount': compound, 'notes': notes}

        this_id = self.__addrow('cluster', dbargs)
        if this_id is None:
            raise ValueError(f'could not add cluster: {cluster_file}')
        return this_id


    def add_feffinp(self, feffinp_file, cif_file=None, cluster_file=None):
        """add a Feff input file to the database

        Parameters
        ---------
        feffinp_file : str or Path
           name or Path of Feff input file
        cif_file : str or Path or None
           name or Path of CIF file [None]
        cluster_file: str or Path or None
           name or Path of cluster file [None]
        """
        cif_id = 0
        if cif_file is not None:
            cif_id = self.add_cif_file(cif_file)
        cluster_id = 0
        if cluster_file is not None:
            cluster_id = self.add_cluster_file(cluster_file)

        try:
            finp = parse_feffinp(feffinp_file)
        except ValueError:
            raise ValueError(f'error parsing feffinp : {feffinp_file}')

        text = compress(finp.pop('text'))
        finp.pop('filename')
        dbargs = {k:v for k, v in finp.items()}
        dbargs['text'] = text
        dbargs['cif_id'] = cif_id
        dbargs['cluster_id'] = cluster_id

        this_id = self.__addrow('feffinp', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feffinp : {feffinp_file}')
        return this_id

    def add_feffdat(self, feffdat, feffinp_file,
                    cif_file=None, cluster_file=None,
                    label=None, description=None,
                    avoid_duplicates=True, rtoler=0.02):
        """add a Feff.dat file to the database

        Parameters
        ---------
        feffdat: str or Path
           name or Path of Feff data file
        feffinp_file:  str or Path
           name or Path of Feff input file (required!)
        cif_file: str or Path or None
           name or Path of CIF file [None]
        cluster_file: str or Path or None
           name or Path of cluster file [None]
        label : str or None
           path label, must be unique [None]
        description: str on None
           path description [None]
        avoid_duplicates: bool
           whether to avoid duplicates [True]
        rtoler: float
           distance tolerance when avoiding duplicates [0.02]

        Notes
        ------
        1. if `label` is `None` it will be built from Absorber, Scatterer,
           distance, and possibly edge.
        2. `label` will be checked for uniqueness
        3. if `description` is None, the Path name will be used.
        4. `avoild duplicates` checks Absorber, Scatterer, distance, and edge
        """

        finp_id = self.add_feffinp(feffinp_file, cif_file=cif_file,
                                   cluster_file=cluster_file)

        try:
            dat = parse_feffdat(feffdat)
        except ValueError:
            raise ValueError(f'error parsing feff.dat file: {feffdat}')

        text = compress(dat.pop('text'))
        fname = dat.pop('filename')

        if avoid_duplicates:
            nearby = self.list_feffdat(absorber=dat['absorber'],
                                       scatterer=dat['scatterer'],
                                       edge=dat['edge'],
                                       rmin=float(dat['reff'])-rtoler,
                                       rmax=float(dat['reff'])+rtoler)
            if len(nearby) > 0:
                print("Avoiding Duplicate entries:")
                s = nearby[0]
                print('This: ', dat['absorber'],  dat['scatterer'],    dat['edge'],  dat['reff'])
                print(s['id'], s['label'], s['absorber'], s['scatterer'], s['edge'], s['reff'])
                return

        if description is None:
            # default description is filenamae and a few parent folders
            words = Path(fname).parts
            n = min(len(words), 2)
            description = Path(*words[-n:]).as_posix()
        if label is None:
            # default label combines absorber, scatterer, reff
            words = [atomic_symbol(dat['absorber']),
                     atomic_symbol(dat['scatterer']),
                     str(round(100*dat['reff']))]
            label = ''.join(words)

        if label is not None:
            # check fie repeated rows
            rows = self.get_rows('feffdat', where={'label': label},
                                 none_if_empty=True)
            if rows is not None:
                words = [atomic_symbol(dat['absorber']),
                         atomic_symbol(dat['scatterer']),
                         str(round(100*dat['reff'])), '_', dat['edge']]
                label = ''.join(words)
                rows = self.get_rows('feffdat', where={'label': label},
                                 none_if_empty=True)

                if rows is not None:
                    olabel, i = label, 0
                    while rows is not None:
                        i += 1
                        label = f'{olabel}_{i}'
                        rows = self.get_rows('feffdat', where={'label': label},
                                             none_if_empty=True)


        dbargs = {k:v for k, v in dat.items()}
        dbargs['text'] = text
        dbargs['feffinp_id'] = finp_id
        dbargs['label'] = label
        dbargs['description'] = description

        this_id = self.__addrow('feffdat', dbargs)
        if this_id is None:
            raise ValueError(f'could not add feff data: {feffdat}')
        return this_id

    def get_feffdat(self, feffid):
        """
        get text of feff.dat, either by 'id' or by 'label' in feffdat table

        Parameters
        ---------
        feffid : int or str
           id or label for Feff.inp

        Returns
        --------
        text of Feff data file.

        See Also
        ---------
        get_feffdat_full() which returns a dict wirh more complete data

        """
        key = 'id' if isinstance(feffid, int) else 'label'
        row = self.get_rows('feffdat', where={key: feffid},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return decompress(row.text)

    def get_feffdat_full(self, feffid):
        """
        return dictionay with full data for a feffid ('id' or 'label' in feffdat table).
        This will include the text Feff.inp and CIF source files, and the name of the
        donator.

        Parameters
        ---------
        feffid : int or str
           id or label for Feff.inp

        Returns
        --------
        dict with keys:  label, absorber, scatterer, reff, nleg, edge,
                         degen, geometry, description,
                         feffdat_id, feffdat feffinp_id, feffinp,
                         cif_id, cif, cluster_id, cluster,
                         donator_id, donator_name, donator_email

        """
        key = 'id' if isinstance(feffid, int) else 'label'
        frow = self.get_rows('feffdat', where={key: feffid},
                            limit_one=True, none_if_empty=True)

        if frow is None:
            raise ValueError(f'could not find feff data: {feffid}')
        out = {}
        for attr in ('label', 'absorber', 'scatterer', 'reff', 'nleg',
                     'edge', 'degen', 'description'):
            out[attr] = getattr(frow, attr)
            if attr in ('absorber', 'scatterer'):
                out[attr] = atomic_symbol(out[attr])
        out['geometry'] = json.loads(frow.geometry)
        out['feffdat_id'] = frow.id
        out['feffdat'] = decompress(frow.text)

        finp = self.get_rows('feffinp', where={'id': frow.feffinp_id},
                            limit_one=True, none_if_empty=True)
        if finp is not None:
            out['feffinp_id'] = frow.feffinp_id
            out['feffinp'] = decompress(finp.text)
            cifrow = self.get_rows('cif', where={'id': finp.cif_id},
                            limit_one=True, none_if_empty=True)
            if cifrow is not None:
                out['cif_id'] = finp.cif_id
                out['cif'] = decompress(cifrow.text)
            elif finp.cluster_id > 0:
                clusterrow = self.get_rows('cluster', where={'id': finp.cluster_id},
                            limit_one=True, none_if_empty=True)
                if clusterrow is not None:
                    out['cluster_id'] = finp.cluster_id
                    out['cluster'] = decompress(clusterrow.text)

        prow = self.get_rows('person', where={'id': frow.donator_id},
                             limit_one=True, none_if_empty=True)
        if prow is not None:
            out['donator_id'] = frow.donator_id
            out['donator_name'] = prow.name
            out['donator_email'] = prow.email
        return out

    def get_feffinp(self, feffinp_id):
        "get text of feff.inp by id in feffinp table"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            return decompress(row.text)

    def get_feffinp_for_feffdat(self, feffid):
        "get text of feff.inp for a Feff.dat file"
        return self.get_feffdat_full(feffid)['feffinp']

    def get_cifinp_for_feffinp(self, feffinp_id):
        "get text of CIF for a feff.inp file"
        row = self.get_rows('feffinp', where={'id': feffinp_id},
                            limit_one=True, none_if_empty=True)
        if row is not None:
            trow = self.get_rows('cif', where={'id': row.cif_id},
                                 limit_one=True, none_if_empty=True)
            if trow is not None:
                return decompress(trow.text)


    def list_feffdat(self, absorber=None, scatterer=None, edge=None,
                     rmin=0., rmax=20.0, with_geometry=True):
        """get a list of feff.dat files matching on one or more criteria:

        Parameters
        ------------
        absorber:   str or None
           symbol for absorber [None for all]
        scatterer:  str or None
           symbol for scatterer [None for all]
        edge:   str or None
           string for absorption edge [None for all]
        rmin :   float
           minimum R value  [0.0]
        rmax :  float
           maximum R value  [20.0]
        with_geometry : bool
           whether to include 'geometry'  [True]
        Returns
        --------
        list of path dictionaries
        """
        wargs = {}
        if absorber is not None:
            if isinstance(absorber, str):
                absorber = atomic_number(absorber.title())
            wargs['absorber'] = absorber
        if scatterer is not None:
            if isinstance(scatterer, str):
                scatterer = atomic_number(scatterer.title())
            wargs['scatterer'] = scatterer
        if edge is not None:
            wargs['edge'] = edge.title()

        rows = self.get_rows('feffdat', where=wargs, limit_one=False)
        out = []
        for row in rows:
            if row.reff > rmin and row.reff < rmax:
                formula = '?'
                finp = self.get_rows('feffinp', where={'id': row.feffinp_id},
                                     limit_one=True, none_if_empty=True)
                if finp is not None and finp.cif_id > 0:
                    cif = self.get_rows('cif', where={'id': finp.cif_id},
                                     limit_one=True, none_if_empty=True)
                    if cif is not None:
                        formula  = cif.formula
                        compound = cif.compound.lower()

                rowdat = {'id': row.id,
                          'label': row.label,
                          'absorber': atomic_symbol(row.absorber),
                          'scatterer': atomic_symbol(row.scatterer),
                          'edge': row.edge,
                          'reff': row.reff,
                          'degen': row.degen,
                          'formula': formula,
                          'compound': compound,
                          'description': row.description}
                if with_geometry:
                    rowdat['geometry'] = json.loads(row.geometry)
                out.append(rowdat)
        return out


    def add_person(self, email, name=None, password=''):
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
                dbargs['name'] = name
            if password is None:
                password = ''
            if len(password) > 1:
                password_ok = check_password_rules(password)
                if not password_ok:
                    raise ValueError('Password is invalid')
                dbargs['password'] = hash_password(password)

            self.__addrow('person', dbargs)

    def get_person(self, email):
        """get person by email"""
        return self.get_rows('person', where={'email': email},
                            limit_one=True, none_if_empty=True)

    def check_person_password(self, email, password):
        """check validity of a person's password"""
        # if len(person

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
