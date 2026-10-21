# Decks held back from this folder

None. Every deck in this folder passes the POTENTIALS-vs-ATOMS audit
(`Python_codes/FEFF_calculations/check_decks.py`).

The five decks previously held back for an ipot/tag mismatch (an old
pymatgen version built POTENTIALS from the unit cell but ATOMS from the
expanded cluster) were regenerated on 2026-08-19 and are included here:
Co-Ni `CoNi_fccSS`, Cu-F `AMCSD_11521`, Ti-O `AMCSD_8037`, Mn-N
`AMCSD_15850`, Ni-O `AMCSD_14357`. Three more decks that carried the same
bug had failed outright rather than producing wrong output (Fe-O
`AMCSD_30` and `AMCSD_429`, Ni-O `AMCSD_15481`); they now run and are
included too.

One structure is still absent for an unrelated reason: **Co-O
`AMCSD_17196_R2.54` (CoAg(N3O4)2)**. Its deck is clean, but feff8l stops
at the standard 6.0 A cluster radius with `tell authors to INCREASE NOVP`
(muffin-tin overlap in a dense azide/nitrate cluster), so it produces no
`.dat`. It runs at 4.0-5.0 A, but using a smaller radius for one structure
would break the fixed-radius convention, so it is left pending a decision.

