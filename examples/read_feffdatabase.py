from os import listdir
from pathlib import Path

from feffdb import FeffDatabase
feffdb = FeffDatabase()

top_folder = 'database'
cif_folder = 'cif_files'
feffdat_stub = 'FEFF_paths(output)_'

for pair in listdir(top_folder):
    fpath = Path(top_folder, pair, f'{feffdat_stub}{pair}')
    cpath = Path(top_folder, pair, cif_folder)
    if not fpath.exists():
        continue
    for drange in listdir(fpath):
        fpathd = Path(fpath, drange)
        if fpathd.is_dir():
            for run in listdir(fpathd):
                feffinp = Path(fpathd, run, 'feff.inp')
                feffdat = Path(fpathd, run, 'feff0001.dat')
                cif_file = Path(cpath, drange, f'{run}.cif')
                if feffdat.exists() and cif_file.exists():
                    feffdb.add_feffdat(feffdat, feffinp, cif_file=cif_file)
                    print(f'added {feffdat}, {pair=} {drange=} {run=}')
