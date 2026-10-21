from os import listdir
from pathlib import Path

from feffdb import FeffDatabase

def Add_Liao_Calcs():
    top_folder = 'Liao_Calcs'
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
                    feff_inp = Path(fpathd, run, 'feff.inp')
                    feff_dat = Path(fpathd, run, 'feff0001.dat')
                    cif_file = Path(cpath, drange, f'{run}.cif')
                    if feff_dat.exists() and cif_file.exists():
                        feffdb.add_feffdat(feff_dat, feff_inp, cif_file=cif_file)
                        print(f'added {feff_dat}, {pair=} {drange=} {run=}')

def Add_Metals():
    top_folder = 'Metals'
    for calc_dir in listdir(top_folder):
        cpath = Path(top_folder, calc_dir)

        feff_inp = cpath / 'feff.inp'
        feff_dat = cpath / 'feff0001.dat'
        for fname in listdir(cpath):
            if fname.endswith('.cif'):
                cif_file = cpath / fname
        if feff_dat.exists() and cif_file.exists():
            feffdb.add_feffdat(feff_dat, feff_inp, cif_file=cif_file)
            print(f'added {feff_dat}, {cif_file} ')
##
if __name__ == '__main__':
    feffdb = FeffDatabase('../feffdat.db')
    Add_Liao_Calcs()
    Add_Metals()
    feffdb.close()
