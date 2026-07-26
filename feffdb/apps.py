import sys
from argparse import ArgumentParser

from pathlib import Path
from pyshortcuts import uname, make_shortcut, ico_ext
import tabulate

from .utils import DBNAME_DEFAULT
from .feffdb import create_feffdb
def feffdb_cli():
    """
    feffdb command-line app
    """
    parser = ArgumentParser(description='Feff Database')
    parser.add_argument('-d', '--dname', dest='dbname',
                       default=None, help=f"database to use [{DBNAME_DEFAULT}]" )
    parser.add_argument('-c', '--create', action='store_true', default=False,
                            help="create new database")
    parser.add_argument('--rmin', action='store_true', default=0,
                        help='minimum distance (Ang)')
    parser.add_argument('--rmax', action='store_true', default=10,
                        help='maximum distance (Ang)')
    parser.add_argument('--list', action='store_true', default=False,
                        help='list all absorbing atoms')
    parser.add_argument('absorber', nargs='?',  help='symbol for absorbing element')
    parser.add_argument('scatterer', nargs='?',  help='symbol for scattering element')

    args = parser.parse_args()

    dbname = args.dbname or DBNAME_DEFAULT
    if not Path(dbname).exists():
        if args.create:
            print("will create db ", dbname)
            create_feffb(name=dbname)
        else:
            print(f"database {dbname} does not exist, use '-c' to create")
            return

    feffdb = FeffDatabase(dbname)

    print(f"{feffdb=}")
    print(dbname, Path(dbname).exists())
    print(f'{args=}')
