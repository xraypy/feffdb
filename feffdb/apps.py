import sys
from argparse import ArgumentParser

from pathlib import Path
from pyshortcuts import uname, make_shortcut, ico_ext
from tabulate import tabulate

from .utils import get_feffdb_path
from .feffdb import create_feffdb, FeffDatabase

def feffdb_cli():
    """
    feffdb command-line app
    """
    dbname_default = get_feffdb_path().absolute().as_posix()
    parser = ArgumentParser(description='Feff Database')
    parser.add_argument('-n', '--name', dest='dbname',
                       default=None, help=f"database to use [{dbname_default}]" )
    parser.add_argument('-c', '--create', action='store_true', default=False,
                            help="create new database")
    parser.add_argument('--rmin',  default=0,
                        help='minimum distance (Ang)')
    parser.add_argument('--rmax',  default=10,
                        help='maximum distance (Ang)')
    parser.add_argument('absorber', nargs='?',
                        help='symbol for absorbing element (use "all" for all absorbers)')
    parser.add_argument('scatterer', nargs='?',
                        help='symbol for scattering element')

    args = parser.parse_args()

    dbname = args.dbname or dbname_default

    if Path(dbname).exists() and args.create:
        print(f"database {dbname} already exists!")

    if not Path(dbname).exists():
        if args.create:
            print("will create db ", dbname)
            create_feffdb(name=dbname)
            return
        else:
            print(f"database {dbname} does not exist, use '-c' to create")
            return

    feffdb = FeffDatabase(dbname)

    absorber = args.absorber
    scatterer = args.scatterer
    out = []
    if absorber is not None or scatterer is not None:
        if scatterer in ('All', 'all', 'None', 'none'):
            scatterer = None
        if absorber in ('All', 'all', 'None', 'none'):
            absorber = None
        rows = feffdb.list_feffdat(absorber=absorber, scatterer=scatterer,
                                   rmin=float(args.rmin), rmax=float(args.rmax))
        for row in rows:
            row.pop('geometry')
            out.append(row)
    if len(out) > 0:
        print(tabulate(out, headers='keys', tablefmt='psql'))
    else:
        parser.print_usage()
