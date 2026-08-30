#!/usr/bin/env python
"""
very simple interface to CIF file for Feff DB
"""
import os
import json
import re
from pathlib import Path
from io import StringIO, IOBase
from charset_normalizer import from_bytes

from xraydb import XrayDB, atomic_mass, atomic_symbol
from xraydb.chemparser import chemparse

from pymatgen.io.cif import CifParser

FEFFDB_NAME  = 'feffdat.db'
FEFFDB_ENV_VAR    = 'FEFF_DB'
LARCHDIR_ENV_VAR  = 'LARCHDIR ' # used for xraypy items
LARCHDIR_DEFAULT  = '.larch'


def get_feffdb_path():
    """get Path to FEFF DB file
    The default is Path('$HOME/.larch/feffdat.db')

    but can be changed with 2 environmental variables:

    1. if LARCHDIR is set, that will be used as the parent folder,
       (with the default '$HOME/.larch'). The database file will be
           LARCHDIR / 'feffdat.db'

    2. if FEFF_DB is set, and the file exists) that will be used.
    """
    dbname = os.environ.get(FEFFDB_ENV_VAR, None)
    if dbname is not None and Path(dbname).exists():
        return Path(dbname)

    parent = Path.home() / os.environ.get(LARCHDIR_ENV_VAR, LARCHDIR_DEFAULT)
    parent.mkdir(mode=0o755, exist_ok=True)
    return parent / FEFFDB_NAME

def read_textfile(filename):
    """read text from a file as string

    Argument
    --------
    filename  (str or file): name of file to read or file-like object

    Returns
    -------
    text of file as string.

    Notes
    ------
    1. the encoding is detected with charset_normalizer.from_bytes
       which is then used to decode bytes read from file.
    2. line endings are normalized to be '\n'.
    """

    text = ''
    def decode(bytedata):
        return str(from_bytes(bytedata).best())

    if isinstance(filename, IOBase):
        text = filename.read()
        if filename.mode == 'rb':
            text = decode(text)
    else:
        with open(Path(filename), 'rb') as fh:
            text = decode(fh.read())
    return text.replace('\r\n', '\n').replace('\r', '\n')


def get_filename_and_text(fname):
    if isinstance(fname, Path):
        fname = fname.absolute().resolve().as_posix()
        text = read_textfile(fname)
    elif isinstance(fname, str) and len(fname) < 255:
        fname = Path(fname).absolute().resolve().as_posix()
        text = read_textfile(fname)
    else:
        text = fname
        fname = '<unknown>'
    return fname, text

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



if __name__ == '__main__':
    print("CIF")
    out = parse_cif('../fayalite.cif')
    print(out.keys())
    print(len(out['text']))
    for key, val in out.items():
        if key != 'text':
            print(key, val)

    print("FEFF:")
    out = parse_feffdat('../feff0001.dat')
    print(out.keys())
    print(len(out['text']))
    for key, val in out.items():
        if key != 'text':
            print(key, val)
