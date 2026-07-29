import sys
from argparse import ArgumentParser

from pathlib import Path
from pyshortcuts import uname, make_shortcut, ico_ext
from tabulate import tabulate

from .utils import DBNAME_DEFAULT
from .feffdb import create_feffdb, FeffDatabase
def feffdb_cli():
    """
    feffdb command-line app
    """
    parser = ArgumentParser(description='Feff Database')
    parser.add_argument('-d', '--dname', dest='dbname',
                       default=None, help=f"database to use [{DBNAME_DEFAULT}]" )
    parser.add_argument('-c', '--create', action='store_true', default=False,
                            help="create new database")
    parser.add_argument('--rmin',  default=0,
                        help='minimum distance (Ang)')
    parser.add_argument('--rmax',  default=10,
                        help='maximum distance (Ang)')
    parser.add_argument('--list', action='store_true', default=False,
                        help='list all absorbing atoms')
    parser.add_argument('absorber', nargs='?',  help='symbol for absorbing element')
    parser.add_argument('scatterer', nargs='?',  help='symbol for scattering element')

    args = parser.parse_args()

    dbname = args.dbname or DBNAME_DEFAULT

    if Path(dbname).exists() and args.create:
        print(f"database {dbname} already exists!")

    if not Path(dbname).exists():
        if args.create:
            print("will create db ", dbname)
            create_feffdb(name=dbname)
        else:
            print(f"database {dbname} does not exist, use '-c' to create")
            return

    feffdb = FeffDatabase(dbname)


    out = []
    if args.list:
        rows = feffdb.list_feffdat(absorber=args.absorber, scatterer=args.scatterer,
                                rmin=float(args.rmin), rmax=float(args.rmax))
        for row in rows:
            row.pop('geometry')
            out.append(row)
        print(tabulate(out, headers='keys', tablefmt='psql'))
    else:

        print(f'{args=}')
