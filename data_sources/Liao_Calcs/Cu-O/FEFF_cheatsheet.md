# FEFF input & output files — what the important parameters mean

_Reference for action items 1 & 2 (explain one .inp, explain one output file). Examples are from the
real CuO run in `FEFF_paths/...CollCode16025/`._

---

## A. The input file `feff.inp` — key cards

```
TITLE  ... CuO, C2/c ...
EDGE   K
CONTROL  1   1    1    1     1      1     * pot xsph fms paths genfmt ff2chi
PRINT    1   0    0    0     0      3
POTENTIALS
 *ipot  Z   tag   lmax1 lmax2  xnatph  spinph
   0   29   Cu     -1    -1    0.0001    0
   1    8   O      -1    -1    4         0
ATOMS
 *  x        y        z      ipot  tag   distance
  0.0000   0.0000   0.0000    0    Cu    0.000     <- absorber at origin
 -1.1547  -1.1349  -1.0881    1    O     1.951
  ...
END
```

- **TITLE** — free-text label (structure summary). No physics; just bookkeeping.
- **EDGE K** — which absorption edge = which core electron the X-ray ejects. **K = 1s**. Sets the
  core-hole and the energy reference for the calculation.
- **S02** — amplitude reduction factor S₀² (0–1), many-body / passive-electron losses. Often left at
  1.0 in the .inp and **refined during the fit** (in your notebook Larch applies it, e.g. s02 = 0.9).
- **CONTROL  pot xsph fms paths genfmt ff2chi** — switches each FEFF *module* on(1)/off(0):
  - `pot` = atomic potentials, `xsph` = phase shifts, `fms` = full multiple scattering,
    `paths` = enumerate scattering paths, `genfmt` = write the `feffNNNN.dat` path files,
    `ff2chi` = sum paths into χ(k).
- **PRINT** — how verbose each module's output is (higher = more detail / more files).
- **POTENTIALS** — one row per *unique* atom type ("unique potential"):
  - `ipot` = index used by ATOMS (**0 = the absorbing atom**),
  - `Z` = atomic number, `tag` = element label,
  - `lmax1`/`lmax2` = max angular momentum for potentials / FMS (`-1` = let FEFF choose),
  - `xnatph` = stoichiometric count of that atom type (used for potential averaging),
  - `spinph` = spin.
- **ATOMS** — Cartesian coordinates (Å) of every atom in the cluster around the absorber:
  - `x y z`, `ipot` (links to POTENTIALS), `tag`, and `distance` from the absorber.
  - The **absorber sits at the origin with ipot 0**; neighbors define the scattering paths.
- **RADIUS / RPATH / RMAX** — cluster / path-length cutoff: how far out to include atoms & paths.
  (In your notebook this is set via the `radius` argument; a small radius keeps just the first shell.)
- **Others you may see:** `EXCHANGE` (exchange-correlation model), `SCF` (self-consistent potential
  radius), `EXAFS` (max k), `NLEG` (max legs per path), `COREHOLE`.

---

## B. The output path file `feffNNNN.dat` — one scattering path

This is the file you actually fit against. **One file = one path** (filename number = path index).

**Header line (the geometry of the path):**
```
 2   2.000   1.9508   2.4188   0.01423   nleg, deg, reff, rnrmav(bohr), edge
```
- **nleg** — number of legs. **2 = single scattering** (absorber → neighbor → back); >2 = multiple scattering.
- **deg** — degeneracy = how many identical paths this represents (e.g. 4 equivalent Cu–O bonds).
- **reff** — effective half-path length = **the bond distance R** (for single scattering). The fit refines
  `R = reff + ΔR`, so this is the *starting* distance, not the final answer.
- then the absorber + neighbor atom list (which atoms, their `ipot`, coordinates).

**Data columns (each a function of photoelectron wavenumber k):**
```
 k   real[2*phc]   mag[feff]   phase[feff]   red factor   lambda   real[p]
```
- **k** — photoelectron wavenumber (Å⁻¹).
- **mag[feff]** — |F(k)|, magnitude of the effective backscattering amplitude ("how strongly this
  neighbor scatters").
- **phase[feff]** — phase of the scattering amplitude (the neighbor's contribution to the total phase).
- **real[2*phc]** — real part of 2× the central (absorber) atom phase shift (the absorber's contribution
  to the total phase).
- **red factor** — amplitude reduction factor along the path.
- **lambda** — photoelectron mean free path λ(k) in Å — damps contributions from distant shells.
- **real[p]** — real part of the complex momentum p.

**How it's used — the EXAFS equation.** These columns plug into:

  χ(k) = Σ_paths [ N·S₀²·|F(k)| / (k·R²) ] · sin(2kR + φ(k)) · exp(−2σ²k²) · exp(−2R/λ(k))

where N = deg, R = reff + ΔR, φ = phase[feff] + central phase. `feffNNNN.dat` supplies **F(k), φ(k),
λ(k), reff**; the **fit refines S₀², ΔE₀, ΔR, σ²**.

---

## C. Other output files (context)

- **`list.dat` / `files.dat`** — index of all paths: path #, degeneracy, R_eff, amplitude ratio %.
  (Your `load_paths()` reads `list.dat`.)
- **`paths.dat`** — the full geometry of every path (atoms, leg lengths).
- **`xmu.dat`** — the full spectrum; columns: `omega` (photon energy eV), `e` (energy rel. E₀),
  `k`, `mu` (total μ), `mu0` (atomic background), `chi` (EXAFS χ).
- **`chi.dat`** — k vs total χ(k) summed over all paths (the EXAFS signal directly).
- **`feff8l.log`** — run log; first place to look if a run fails.
- Intermediate (ignore): `pot.*`, `phase.pad`, `*.json`, `feff.pad`, `HEADER/ATOMS/POTENTIALS/PARAMETERS`.
