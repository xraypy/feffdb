# feff_convert.py: what the executables and the source say

The draft script had one fatal bug and two silent ones. The fatal bug is cosmetic to fix: the
`feffNNNN.dat` header regex matches nothing, so `path_signatures()` always returned an empty
set. The two silent bugs are the reason to care about this exercise. First, `CONTROL` and
`PRINT` are copied across versions unchanged, but their flag lists are not the same list with
entries added — the four FEFF6 flags do not line up with the first four FEFF8 flags, so a
converted file runs to completion and quietly computes something else. Second, the script
invents `-1 -1 1` for the POTENTIALS columns FEFF6 does not have, and the third of those
placeholders switches FEFF8.5L from counting atoms to trusting the card, which moves the
interstitial potential. Neither produces an error, a warning, or a non-zero exit status.

Everything below is either observed by running an executable or quoted from source with a file
and line. Where neither was possible it is marked ASSUMED and should be treated as no better
than the original table.

Environment: macOS 15 (arm64), `feff6l` and `feff8l` from xraylarch 2026.2.2
(`/opt/homebrew/lib/python3.11/site-packages/larch/bin/darwin64/`), banners `Feff 6L.02` and
`Feff8L (EXAFS) release 0.1`. No gfortran was needed; both binaries ship compiled. FEFF9 and
FEFF10 were never downloaded, run, or read.

---

## 1. Observed by running

Test structure, written by hand for this exercise (`tests/inputs/cu_fcc_feff6.inp`): fcc Cu,
a = 3.615 Å, K edge, every lattice site within 6.0 Å of the absorber, 79 atoms, two unique
potentials, `RMAX 6.0`, `NLEG 4`, `CRITERIA 4.0 2.5`, `DEBYE 300 315`.

### 1.1 The two native runs

| | feff6l | feff8l |
|---|---|---|
| command | `feff6l` in the run directory | `feff8l` in the run directory |
| exit status | 0 | 0 |
| unique paths examined / kept | 25 / 22 | 20 / 20 |
| `feffNNNN.dat` | 22 | 20, **only** with `PRINT`'s sixth flag at 3 |
| `chi.dat` | **not written** | written |
| other output | `paths.dat files.dat misc.dat nstar.dat phase.bin phase.pad feff.run` | `paths.dat list.dat misc.dat xmu.dat chi.dat feff.pad pot.pad phase.pad` + seven `.json` files |
| absorber muffin-tin radius | Rmt 1.293 bohr | Rmt 1.451 bohr |
| Fermi level | Mu = −5.501 eV | Mu = −3.733 eV |

Two things in that table are not version differences in the physics but defaults worth pinning.
`chi.dat` is missing from FEFF6L because this build never calls the module: `src/feff6l/feff.f:150`
is `c         call ff2chi (...)`, commented out. And FEFF8L's header line reads
`POT  Non-SCF, core-hole, AFOLP (folp(0)= 1.150)` — it overlaps every muffin tin by 15% unless
told otherwise, which is where most of the Rmt and Mu difference comes from.

For the first-shell single-scattering path, present in both at reff = 2.5562 Å, degeneracy 12:

| k (Å⁻¹) | \|feff\| feff6l | \|feff\| feff8l | ratio | Δ phase (rad) |
|---|---|---|---|---|
| 4 | 0.3226 | 0.3256 | 1.009 | −0.014 |
| 8 | 0.7148 | 0.7241 | 1.013 | −0.007 |
| 12 | 0.3635 | 0.3715 | 1.022 | −0.019 |

Geometry is stable to the printed precision; amplitude is not, by 1–2% over the usable range.
That is small enough to be invisible in a fit and large enough to move S0².

### 1.2 Failure variants

"Loud" below means the run stops and says why. Note that **exit status is never a reliable
signal** with these wrappers: every one of these runs returned 0, including the fatal ones.

| variant | executable | result |
|---|---|---|
| `CONTROL 1 1 1` (3 flags) | feff6l | **Loud.** `Error reading input, bad line follows: CONTROL 1 1 1` / `Fatal Error: at RDINP`. Exit 0. |
| `CONTROL 1 1 1` (3 flags) | feff8l | **Loud.** `RDINP fatal error` / `#ERROR STOP`, then every later module prints `failed to read geom.json`. Exit 0. |
| `CONTROL 1 1 1 1 1 1` (6 flags) | feff6l | **Silent.** Extra flags ignored, `feff0001.dat` byte-identical to the native run. |
| `CONTROL 1 1 0 1 1 1` (valid FEFF8 card, FMS off) | feff6l | **Silent and wrong.** FEFF6 reads the third flag as genfmt, so genfmt is skipped: zero `feffNNNN.dat`, and the log still ends `Feff done. Have a nice day.` |
| `PRINT 1 0 0 0 1 3` (6 flags) | feff6l | **Silent.** Extra flags ignored, output identical. |
| `PRINT 1 0 0 0` (4 flags) | feff8l | **Silent.** Read as a FEFF7 card; the run completes with `chi.dat` and **no `feffNNNN.dat` at all**. |
| POTENTIALS with 6 columns | feff6l | **Silent.** Columns past the tag ignored, output identical. |
| POTENTIALS with 3 columns | feff8l | Fine — columns 4–7 are optional. |
| POTENTIALS `0 29 Cu -1 -1 1` (the script's placeholder) | feff8l | **Silent and wrong.** Mu −3.733 → −4.173 eV, Vint −16.37 → −17.44 eV, Rs_int 1.992 → 1.944. No message. |
| `EDGE K` + `S02 1.0` | feff6l | **Loud.** `Unknown keyword: "EDGE"` / `See FEFF document for valid keywords.` Exit 0. |
| `HOLE 1 1.0` | feff8l | Accepted, runs normally. |

### 1.3 Path matching

The header line is the same in both versions, and it is not what the draft regex expected:

```
   2  12.000   2.5562    2.6412   -5.50118 nleg, deg, reff, rnrmav(bohr), edge
```

The order is nleg, degeneracy, reff — the draft read group 2 as nleg, group 3 as degeneracy and
group 4 as reff, and in any case keyed on the words `index` and `r =`, which do not appear.

Matching on `(reff, nleg, degeneracy)` as the design guide proposed is not enough to tell paths
apart: 22 FEFF6L files collapse to 17 signatures and 20 FEFF8L files to 15, because fcc Cu has
three distinct 4-leg paths at reff 5.112 Å with degeneracy 12. Adding the scatterer coordinates
makes the signature unique but destroys portability — the two pathfinders pick different
symmetry-equivalent representatives of the same path, and only 7 of 22 then match across
versions. What works is the path's shape: walk it from the absorber and record the potential
index, leg length and scattering angle at each vertex, in whichever traversal direction sorts
first. That is unique within each run (22/22 and 20/20) and portable.

| signature | unique in feff6l | unique in feff8l | shared |
|---|---|---|---|
| (reff, nleg, deg) | 17 of 22 | 15 of 20 | 15 |
| + scatterer ipots + sorted leg lengths | 18 of 22 | 16 of 20 | 15 |
| + sorted scattering angles | 19 of 22 | 18 of 20 | 16 |
| ordered (ipot, leg, angle), direction-canonical | **22 of 22** | **20 of 20** | **18** |

Of the 18 shared paths, three land on different file numbers in the two runs
(`feff0022` ↔ `feff0017`, `feff0019` ↔ `feff0016`, `feff0025` ↔ `feff0020`), which is the
concrete reason never to match by index. FEFF6L finds 4 paths FEFF8L does not (two 3-leg paths
at 5.705 Å with degeneracies 48 and 96, among others); FEFF8L finds 2 FEFF6L does not.

### 1.4 The converted files run

`feff6 → feff85l` under `feff8l`: exit 0, 19 `feffNNNN.dat`, `chi.dat` written. Nineteen rather
than the native twenty because the source `PRINT` asked genfmt for the filtered set, not all
paths — the conversion carried that choice over rather than changing it.

`feff85l → feff6` under `feff6l`: exit 0, 25 `feffNNNN.dat`. Twenty-five rather than the native
twenty-two because the source `PRINT` had genfmt at level 1, "keep all", and that too carried
over.

---

## 2. Read in documentation and source

All from `github.com/xraypy/feff85exafs` at the current main, cloned to `/tmp/f85src`. The repo
carries a BSD-style `LICENSE` and `LICENSE_Feff6L.txt`; nothing from it was copied into the
script or the tests beyond card names and flag meanings.

**a. CONTROL flags.**
FEFF6L takes four — potph, paths, genfmt, ff2chi, default `1 1 1 1`
(`doc/feff6l_doc.txt:397-405`; parsed at `src/feff6l/rdinp.f:216-223`, which reads `words(2)`
through `words(5)`).
FEFF8.5L takes six — mpot, mphase, mfms, mpath, mfeff, mchi (`src/RDINP/rdinp_l.f:201-219`).
If it finds only four it treats the card as FEFF7 input and copies the first flag into mpot,
mphase **and** mfms (`rdinp_l.f:204-210`) rather than rejecting it.

**b. PRINT flags.**
FEFF6L takes four, same four modules (`doc/feff6l_doc.txt:477-506`; `src/feff6l/rdinp.f:296-312`).
FEFF8.5L takes six — pot, xsph, fms, pathfinder, genfmt, ff2x (`rdinp_l.f:318-364`), with the
same four-flag FEFF7 fallback (`rdinp_l.f:350-356`). The flag that matters for this tool is the
sixth: `ipr6` 3 is "add feffnnnn.dat for each path" and 4 adds `chipnnnn.dat` as well
(`rdinp_l.f:341-347`). In FEFF6 those files come from genfmt instead
(`doc/feff6l_doc.txt:498-500`). This is the single most important difference for anyone
converting a file in order to get path files out.

**c. POTENTIALS columns.**
FEFF6L reads three: `ipot Z tag`, and the tag is optional (`doc/feff6l_doc.txt:440-476`;
`src/feff6l/rdinp.f` mode-3 block, which reads `words(1)`, `words(2)` and `words(3)` if
`nwords >= 3`). Columns past the third are not read and not complained about.
FEFF8.5L reads up to seven (`src/RDINP/rdinp_l.f:703-741`): `ipot Z tag lmaxsc lmaxph
stoichiometry spin`, each guarded by its own `nwords >=` test, so all four extras are optional.
Defaults: `lmaxsc` is 1, 2 or 3 by atomic number (Z < 6, Z < 55, else) and `lmaxph` is 3, or 2
for Z < 6. Values outside 1…lx in columns 4 and 5 are discarded and the default kept — which
is why the script's `-1 -1` placeholders did no harm. The stoichiometry column does harm: any
value there sets `lxnat = 1` (`rdinp_l.f:737`), and at `rdinp_l.f:935-960` `lxnat` decides
whether the code counts each potential's atoms from the ATOMS list or takes the number from the
card and normalises it to one absorber. Writing `1` for an fcc Cu neighbour shell of 78 atoms is
a different structure.

**d. HOLE vs EDGE/S02.**
FEFF6L has no EDGE and no S02 card. Its keyword table (`src/feff6l/rdinp.f:834-898`) contains
`HOLE` and nothing else for this; an unrecognised keyword hits the final `else` at
`rdinp.f:434-442` and calls `fstop`. `HOLE ihole S02` is documented at
`doc/feff6l_doc.txt:421-439`, hole codes 0 (none), 1 (K), 2 (L1), 3 (L2), 4 (L3).
FEFF8.5L accepts all three: `HOLE` (`rdinp_l.f:187-192`), `EDGE` via `setedg`
(`rdinp_l.f:493-497`) and `S02` (`rdinp_l.f:547-550`). They interact: `HOLE`'s second argument
goes into `s02h`, and `rdinp_l.f:1014` reads `if (s02.eq.1.d0) s02 = s02h`, so an explicit
`S02 1.0` loses to a non-default value on the `HOLE` card.

**e. Which cards each version accepts.**
Both parsers compare only the first four characters of a keyword (`src/feff6l/rdinp.f:826-833`,
`src/COMMON/itoken.f:1-11`), so `POTENTIAL` and `POTENTIALS` are the same card. The full
tables are at `src/feff6l/rdinp.f:834-898` (32 keywords) and `src/COMMON/itoken.f:17-140`
(63 keywords); both are transcribed into `F6_CARDS` and `F85_CARDS` in the script.

The draft's `CORE` set held 10 cards where FEFF6L accepts 32 and FEFF8.5L 63, so `SIG2`,
`FOLP`, `OVERLAP`, `POLARIZATION`, `AFOLP`, `CORRECTIONS` and a dozen more would have been
dropped from any file that used them. The design guide's shared list also named `RPATH`, which
FEFF6L does not have — it takes `RMAX`, while FEFF8.5L accepts either (`itoken.f:33`).
`V8_EXTRA` listed `COREHOLE`,
which is **not** in FEFF8.5L's table at all — writing it would abort the run. The core-hole
switch there is `NOHOLE` (`rdinp_l.f:464-470`).

FEFF8.5L also has a third category the draft had no room for: thirteen cards it recognises,
announces it cannot do, and then ignores — XANES, FMS, LDOS, XES, DANES, FPRIME, XMCD/XNCD,
TDLDA, PMBSE, ELNES, EXELFS, MAGIC and EGRID (`rdinp_l.f:402, 526, 530, 552, 556, 562, 574,
588, 593, 620, 625, 630, 641`). So the FMS the draft assumed FEFF8.5L would run is not run.
SCF, by contrast, is fully supported (`rdinp_l.f:498-522`).

**f. Two more defaults worth pinning.** Both versions default to Hedin-Lundqvist exchange,
`ixc = 0` (`src/feff6l/rdinp.f:61`, `src/RDINP/iniall.f:41`), so compatible mode can now write
`EXCHANGE 0 0 0` with evidence behind it. Muffin-tin overlap does not match: FEFF6L defaults
`folp` to 1.0 (`src/feff6l/rdinp.f:128`) and FEFF8.5L to 1.15 (`rdinp_l.f:70`, applied to every
potential at `rdinp_l.f:1059-1063` unless a `FOLP` card is present). That gap is left as a
warning rather than written automatically, since it needs one card per potential.

**g. Comment characters.** `*`, `%`, `#` and `;` (`src/COMMON/str.f:192-198`;
`src/feff6l/rdinp.f:903-910` lists `*#;`). The draft stripped only `*` and `#`.

---

## 3. Assumed / unverified

- **Everything about FEFF8.2/8.4, FEFF9 and FEFF10.** The `feff8`, `feff9` and `feff10`
  profiles are copies of the FEFF8.5L table with guesses bolted on. They are now marked
  `verified=False` and the converter emits a warning naming them as assumed, but the content is
  no better than the draft's.
- **That FEFF8.2/8.4 behaves like FEFF8.5L on CONTROL, PRINT and POTENTIALS.** Plausible — 8.5L
  is derived from that code — but untested here.
- **Executable names.** `feff85l` was never found on this machine; larch installs the binary as
  `feff8l`, so that name now comes first in the candidate list. The names for 8.2/8.4, 9 and 10
  are guesses.
- **`chi.dat` from FEFF6L.** Absent here because this build's `ff2chi` call is commented out.
  Whether other FEFF6L builds write it was not checked.
- **The 1–2% amplitude difference** is one structure, one edge, one path. It is an existence
  proof that amplitudes move, not a calibration.
- **Hole codes above 4** are passed through to FEFF6 unchanged with a warning; what FEFF6L
  actually does with them was not tested.

---

## 4. Changes made

Full diff against the draft (indentation repaired only) in `evidence/feff_convert.diff`, also
`git diff` between the two commits in this folder. In summary:

1. **Fixed the header regex and rewrote `path_signatures()`** around the real
   `nleg, deg, reff, rnrmav, edge` line, with the shape-based signature from §1.3 and a
   `read_path()` helper that returns one file's signature.
2. **`translate_flags()`** converts `CONTROL` and `PRINT` between the 4-flag and 6-flag
   layouts instead of copying them, warning on every lossy step: mfms forced to 0 going up
   (FEFF8.5L has no FMS), mfms dropped going down, ff2x print level set to 3 going up so path
   files are written, clamped to 2 going down.
3. **POTENTIALS columns are never invented.** Missing columns stay missing; surplus columns are
   truncated to the target's maximum with a warning naming them. `pot_columns` is now a ceiling,
   not a required count.
4. **Keyword tables rebuilt from source** for FEFF6L and FEFF8.5L, keyed on four characters, with
   a new `ignored` set for the cards FEFF8.5L accepts and discards.
5. **`run()` reads the log, not just the exit status**, because the larch wrappers return 0 after
   a fatal RDINP error.
6. **Comment stripping now covers `%` and `;`.**
7. Compatible mode writes `EXCHANGE 0 0 0` for FEFF8.5L and warns about the AFOLP gap; unverified
   targets keep the old "pin it by hand" warning.
8. Smaller fixes: warnings no longer accumulate across repeated `convert()` calls and no longer
   come out in reverse order inside the file; the edge-code map had L1 and L2 the right way round
   but is now written in order; `TITLE` and other cards keep their original spelling in the output.

Tests: `tests/test_convert_unit.py` (30 tests, no executables) and `tests/test_convert_exec.py`
(8 tests, skipped without `feff6l`/`feff8l`). `python3 -m pytest tests -q` → 38 passed.

---

## 5. Proposed corrections to the PROFILES table

| field | draft | corrected | evidence |
|---|---|---|---|
| `CORE` shared cards | 10 cards; `SIG2`, `FOLP`, `OVERLAP`, `POLARIZATION` and 18 others missing | FEFF6L 32 keywords, FEFF8.5L 63, held separately | `src/feff6l/rdinp.f:834-898`; `src/COMMON/itoken.f:17-140` |
| keyword comparison | whole word | first four characters | `src/feff6l/rdinp.f:826-833`; `src/COMMON/itoken.f:1-11` |
| `RPATH` | in `CORE` | FEFF8.5L only; FEFF6L has `RMAX` | `itoken.f:33`; absent from FEFF6L table |
| `COREHOLE` in `V8_EXTRA` | allowed | not a FEFF8.5L card; would abort. Use `NOHOLE` | `rdinp_l.f:464-470`; no `CORE` entry in `itoken.f` |
| `FMS` in `V8_EXTRA` | allowed and meaningful | recognised, then ignored with a message | `rdinp_l.f:523-528` |
| `XANES`, `LDOS` in `V8_EXTRA` | allowed | recognised, then ignored | `rdinp_l.f:400-404, 529-532` |
| `SCF` in `V8_EXTRA` | allowed | correct — fully supported | `rdinp_l.f:498-522` |
| `pot_columns = 3 / 6` | required column count | maximum: 3 for FEFF6L, 7 for FEFF8.5L, all past the second optional | `doc/feff6l_doc.txt:440-476`; `rdinp_l.f:703-741` |
| POTENTIALS placeholders `-1 -1 1` | filled in silently | never written; the stoichiometry placeholder moves Mu by 0.44 eV | `rdinp_l.f:737, 935-960`; [RUN] |
| `edge_style` | FEFF6 `HOLE`, 8+ `EDGE` | correct, and FEFF8.5L takes `HOLE` too | `rdinp_l.f:187-192, 493-497`; [RUN] |
| CONTROL/PRINT | passed through | 4-flag and 6-flag layouts translated | `rdinp.f:216-223, 296-312`; `rdinp_l.f:201-219, 318-364` |
| `feff85l` exe names | `("feff85l", "feff8l")` | `("feff8l", "feff85l")` — larch installs `feff8l` | [RUN] |
| `feff8`, `feff9`, `feff10` | presented as fact | marked assumed, warning emitted | no evidence either way |

---

## 6. For someone with a FEFF9 or FEFF10 license

1. How many flags do `CONTROL` and `PRINT` take, and in what order? Is there still a four-flag
   FEFF7 fallback, and does it silently remap the flags the way FEFF8.5L does?
2. Which print flag produces `feffNNNN.dat`? If it is still the last one at level 3, the
   converter needs no change for 9 and 10.
3. How many POTENTIALS columns are read, and does supplying the stoichiometry column still
   switch the code from counting atoms to trusting the card?
4. Is `COREHOLE` a real card there, and what is its syntax? If it is, compatible mode can pin it
   the way `EXCHANGE` is pinned for 8.5L.
5. What is the default muffin-tin overlap? If it is 1.15 like 8.5L, compatible mode should write
   `FOLP <ipot> 1.0` for every potential when the target is 9 or 10.
6. Does `HOLE` still work, or is `EDGE` now required?
7. Is the `feffNNNN.dat` header still `nleg, deg, reff, rnrmav(bohr), edge` in that order? The
   regex depends on it.
8. Is an unrecognised keyword fatal, or a warning?
9. What is the executable actually called after a default install?

---

## 7. Still open

- **The warning about `EXCHANGE` and the core hole for FEFF8.2/8.4, 9 and 10 is unchanged**,
  because nothing could be verified for those versions. For FEFF8.5L the gap is now closed:
  `EXCHANGE 0 0 0` is written in compatible mode, and `COREHOLE` turned out not to exist.
- **Compatible mode is still not FEFF6-equivalent** even for FEFF8.5L, because of the 1.15
  default overlap. Closing that means writing one `FOLP` card per potential; it is a one-line
  change if that is wanted.
- **`cif2feffinp`'s `version8` option** was not checked — larch 2026.2.2 is installed here and
  the question is worth five minutes, but it is outside what the brief asked for.
- **One structure, one edge.** Every number here comes from fcc Cu at the K edge. A second
  structure with two different scatterers would test the POTENTIALS handling much harder.
