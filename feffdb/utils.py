#!/usr/bin/env python
"""
very simple interface to CIF file for Feff DB
"""
import json
import os
import shutil
import sqlite3
import re
import lzma
from io import IOBase
from charset_normalizer import from_bytes
from pathlib import Path
from platformdirs import user_data_dir
from warnings import warn
from xraydb import XrayDB, atomic_mass, atomic_symbol
from xraydb.chemparser import chemparse
from pyshortcuts import read_textfile

from pymatgen.io.cif import CifParser

from .schema import feffdb_schema, VERSIONS

FEFFDB_NAME  = 'feffdat.db'
LARCHDIR_ENV = 'LARCHDIR '
LARCHDIR_DEF = '.larch'


def is_feffdb(db: str|sqlite3.Connection) -> bool:
    """test if database file or open connection is a valid Feffdata DB

    a valid FEFFDB file has tables 'feffdat', 'feffinp', 'cif', 'element', and 'info'
    """

    feffdb_tables = ("element", "info", "feffdat", "feffinp", "cif")
    if isinstance(db, sqlite3.Connection):
        dbconn = db
    else:
        try:
            dbconn  = sqlite3.connect(db)
        except Exception:
            return False

    cursor = dbconn.cursor()
    cursor.execute("select name from sqlite_master where type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    dbconn.close()

    return all([tab in tables for tab in feffdb_tables])


def get_feffdb(dbname:str|Path|None=None) -> Path:
    """return Path to FEFF DB file

    Parameters
    ----------
    dbname : str or None
        name or Path of the Feff Database or None

    Returns
    --------
    Path of Feff database to use.

    Notes
    ------
    1. First, if the passed dbname is a valid FeffDB, that is used.
    2. Then, if the Environmental Variable FEFFDB_FILE is set (and
       is a valid FeffDB), that is used.
    3. Then `platformsdir.user_data_dir()` is used to find a
       `feffdb` folder. if `feffdat.db` exists, that is used.
    4. Then, `platformsdir.user_data_dir('feffdb')` is created and
       "feffdat.db" from the source directory is copied there, and
       that copy is used.
    5. Finally, "feffdat.db" from the source directory is used.
    """
    if dbname is None:
        dbname = os.environ.get('FEFFDB_FILE', None)
    if is_feffdb(dbname):
        return Path(dbname)

    parent = Path(user_data_dir('feffdb', appauthor=False))
    try:
        parent.mkdir(mode=0o755, exist_ok=True)
    except FileNotFoundError:
        pass
    dbpath = parent / FEFFDB_NAME
    if is_feffdb(dbpath):
        return dbpath

    installed = Path(__file__).parent / FEFFDB_NAME
    try:
        shutil.copy(installed, dbpath)
        if is_feffdb(dbpath):
            return dbpath
    except Exception:
        warn(f'could not install {FEFFDB_NAME} to {parent}')
    return installed


def create_feffdb(dbname=None):
    """create FeffData.DB

    Parameters
    ----------
    dbname : str or None
        name or Path of the Feff Database or None

    """
    if dbname is None:
        dbpath = get_feffdb()
    else:
        dbpath = Path(dbname)
        if dbpath.exists():
            raise IOError(f"file {dbname} already exists")
        dbpath.parent.mkdir(parents=True, mode=0o755, exist_ok=True)

    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    for t in feffdb_schema.split(';'):
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


def get_filename_and_text(input: str|Path, allow_text=True):
    """given a filename or Path  returns absolute_pathname, text

    input can either be a filename that resolves to an existing Path or
    an existing Path. In both cases, the return value is
        absolute_pathname, text

    if `input` is not an existing file name or path, and `allow_text` is True,
    then `patname` is set to `<unknown>` and the input text is returned as `text`

    """
    fpath, text = '<unknown>', None
    if isinstance(input, str):
        fpath = Path(input)
        if fpath.exists():
            input = fpath

    if isinstance(input, Path) and input.exists():
        fpath = input.absolute().resolve().as_posix()
        text = read_textfile(fpath)
    if text is None and isinstance(input, str) and allow_text:
        fpath = '<unknown>'
        text = input
    return fpath, text

def compress(val, encoding='utf-8'):
    "lzma compress text value"
    return lzma.compress(val.encode(encoding))

def decompress(val, encoding='utf-8'):
    "lzma decompress value to text"
    return lzma.decompress(val).decode(encoding)

def parse_cif(ciffile):
    ciffile, ciftext = get_filename_and_text(ciffile)

    try:
        cif = CifParser.from_str(ciftext, occupancy_tolerance=10, site_tolerance=0.005)
    except Exception:
        raise ValueError(f'invalid CIF {ciffile}')

    cifkey = list(cif._cif.data.keys())[0]
    dat = cif._cif.data[cifkey].data

    formula = None
    for formname in ('_chemical_formula_sum', '_chemical_formula_moiety'):
        if formname in dat:
            try:
                parsed_formula = chemparse(dat[formname])
                formula = dat[formname].replace(' ', '')
            except:
                print("Could not parse ", dat[formname])

    if formula is None and '_atom_site_type_symbol' in dat:
        comps = {}
        complist = dat['_atom_site_type_symbol']
        for c in complist:
            if c not in comps:
                nx = complist.count(c)
                comps[c] = '%s%d' % (c, nx) if nx != 1 else c
        formula = ''.join(comps.values())

    if formula is None:
        raise ValueError(f'Cannot read chemical formula from CIF {ciffile}')

    # compound
    compound = '<missing>'
    for compname in ('_chemical_compound_source',
                     '_chemical_name_systematic',
                     '_chemical_name_common',
                     '_chemical_name_mineral'):
        if compname in dat:
            compound = dat[compname]

    # get spacegroup and symmetry
    sgroup_name = dat.get('_symmetry_space_group_name_H-M', None)
    if sgroup_name is None:
        for key, val in dat.items():
            if 'space_group' in key and 'H-M' in key:
                sgroup_name = val

    source_db = ''
    source_id = -1
    amcsd_id = dat.get('_database_code_amcsd', None)
    if amcsd_id is not None:
        source_db = 'amcsd'
        source_id = amcsd_id

    return {'text': ciftext, 'filename': ciffile,
            'formula': formula, 'compound': compound,
            'space_group': sgroup_name,
            'source_db': source_db, 'source_id': source_id}


def parse_feffinp(feffinp):
    """parse feff.inp just enough for FeffDB"""

    feffinp, text = get_filename_and_text(feffinp)

    edge = ''
    absorber = 0
    ipots = []
    natoms = 0
    mode = None
    for line in text.split('\n'):
        line = line.strip()
        if line.startswith('*') or line.startswith('#'):
            continue

        if line.lower().startswith('edge'):
            words = line.split(' ')
            edge = words[1].upper()
        elif line.lower().startswith('potent'):
            mode = 'pot'
        elif line.lower().startswith('atoms'):
            mode = 'atoms'
        elif line.lower().startswith('end'):
            mode = None
        elif mode == 'pot':
            if line.startswith('0'):
                words = line.strip().split()
                absorber = int(words[1])
            elif len(line) > 6:
                words = line.strip().split()
                ipots.append(int(words[1]))
        elif mode == 'atoms':
            try:
                words = line.strip().split()
                w = [float(x) for x in words[:4]]
                natoms += 1
            except (ValueError, TypeError):
                pass

    return {'text': text, 'filename': feffinp, 'absorber': absorber,
            'edge': edge, 'scatterers': json.dumps(ipots), 'natoms': natoms}


def parse_feffdat(feffdatfile):
    """parse feffdat just enough for FeffDB"""
    feffdatfile, fefftext = get_filename_and_text(feffdatfile)

    mode = 'header'
    potentials, geom, data = [], [],[]
    version, pcounter, iline = '', 0, 0
    reff = 0.0
    lines = fefftext.split('\n')

    if 'feff' not in lines[0].lower()[:]:
        raise ValueError(f'Not a valid feff.dat file: {feffdatfile}')

    for line in lines:
        iline += 1
        line = line[:-1].strip()
        if line.startswith('#'):
            line = line[1:].strip()

        if iline == 1:
            title = line[:64].strip()
            version = line[64:].strip()
            continue
        if line.startswith('k') and 'mag[feff]' in line:
            mode = 'arrays'
            break
        elif '----' in line[2:10]:
            mode = 'path'
            continue
        #
        if (mode == 'header' and
            (re.match(r'^Abs\b', line) or re.match(r'^Pot\s+\d+\b', line)) and
            re.search(r'\bZ\s*=', line)):
            words = line.replace('=', ' ').split()
            ipot, z, rmt, rnm = (0, 0, 0, 0)
            words.pop(0)
            if re.match(r'^Pot\s+\d+\b', line):
                ipot = int(words.pop(0))
            iz = int(words[1])
            rmt = float(words[3])
            rnm = float(words[5])
            if re.match(r'^Abs\b', line):
                edge = words[6]
            potentials.append((ipot, iz, rmt, rnm))
        elif mode == 'header' and re.match(r'^Gam_ch\s*=', line):
            pass
        elif mode == 'header' and re.match(r'^Mu\s*=', line):
            pass
        elif mode == 'path':
            pcounter += 1
            if pcounter == 1:
                w = [float(x) for x in line.split()[:5]]
                nleg = int(w.pop(0))
                degen, reff, rnorman, e_edge = w
            elif pcounter > 2:
                words = line.split()
                xyz = [float(x) for x in words[:3]]
                ipot = int(words[3])
                iz   = int(words[4])
                if len(words) > 5:
                    lab = words[5]
                else:
                    lab = atomic_symbol(iz)
                amass = atomic_mass(iz)
                this_geom = [lab, iz, ipot, amass] + xyz
                if len(geom) == 0:
                    absorber = lab
                geom.append(tuple(this_geom))
        elif mode == 'arrays':
            break

    if len(geom) < 2:
        raise ValueError(f'could not read Path from feff.dat file: {feffdatfile}')

    absorber = geom[0][1]
    scatterer = geom[1][1]

    return {'text': fefftext, 'filename': feffdatfile,
            'absorber': absorber, 'scatterer': scatterer,
            'reff': reff,  'degen': degen, 'nleg': nleg,
            'edge': edge, 'geometry': json.dumps(geom)}
