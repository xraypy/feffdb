from time import time
from tabulate import tabulate
from pyshortcuts import debugtimer

from feffdb.feffpath import feffpath as feffpath_x
from larch.xafs import feffpath
from feffdb import FeffDatabase


feffdat_files = ['feffAg_1.dat',
                 'feffCu_1.dat',
                 'feffPd_1.dat',
                 'feffTi_1.dat',]

tag0 = 'ZnCl230'

feffdb_tags = ['AgAg289',
               'CuCu256',
               'PdPd275',
               'TiO199']


dtimer = debugtimer('Timing with FeffDB')

# open the database

fdb =  FeffDatabase('../../feffdat.db', read_only=True)
dtimer.add('Opened database')

pdat = fdb.get_feffdat(tag0)
dtimer.add('got fitst text from Feff data file')

pdat = feffpath(f'feffdb[{tag0}]')
dtimer.add('extracted first Feff data file from db')


for i in range(3):
    for tag in feffdb_tags:
        pdat = feffpath(f'feffdb[{tag}]')
    dtimer.add(f'{i} read {len(feffdb_tags)} Feff data files from FeffDB')

    for fname in feffdat_files:
        pdat = feffpath(fname)
    dtimer.add(f'{i} read {len(feffdat_files)} Feff data files from disk')


dtimer.show(precision=4)
