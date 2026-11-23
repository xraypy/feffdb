from pathlib import Path

from feffdb.utils import parse_cif, parse_feffinp, parse_feffdat

folder   = Path('..', 'source_data', 'Larix', 'Fe1_K_Magnetite_cif9740')
cifpath  = Path(folder, 'Magnetite_cif9740.cif')
finppath = Path(folder, 'feff0001.dat')
fdatpath = Path(folder, 'feff0001.dat')

def test_cif_parse():
    out = parse_cif(cifpath)
    for col in ('text', 'filename', 'space_group', 'formula', 'compound'):
        assert col in out

def test_feffinp_parse():
    out = parse_feffinp(finppath)
    for col in ('text', 'filename', 'absorber', 'scatterers', 'edge', 'natoms'):
        assert col in out


def test_feffdat_parse():
    out = parse_feffdat(fdatpath)
    for col in ('text', 'filename', 'absorber', 'scatterer', 'edge', 'reff', 'nleg'):
        assert col in out
