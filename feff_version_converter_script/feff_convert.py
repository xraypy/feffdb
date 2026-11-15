#!/usr/bin/env python3
"""feff_convert.py - rewrite a feff.inp for a different FEFF version.

Writes input files only; never bundles or redistributes FEFF.
Users supply their own FEFF executables (FEFF9/10 are licensed).

Evidence tags used in the comments below:
  [SRC]  read in feff85exafs source (github.com/xraypy/feff85exafs, BSD licensed)
  [DOC]  read in doc/feff6l_doc.txt shipped with that source
  [RUN]  observed by running feff6l / feff8l (larch 2026.2.2 builds)
  [ASSUMED] not verified - no executable and no source was available
"""
from __future__ import annotations
import argparse, math, os, re, shutil, subprocess, sys, tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- capabilities
# FEFF matches keywords on their first four characters only
# [SRC] src/feff6l/rdinp.f:826-900 (itoken), src/COMMON/itoken.f:17-140.
# Cards are therefore stored and compared as their 4-character key.

def key(card: str) -> str:
    return card.upper()[:4]

def keyset(*cards: str) -> frozenset:
    return frozenset(key(c) for c in cards)


@dataclass(frozen=True)
class Profile:
    name: str
    edge_style: str       # "HOLE" -> "HOLE ihole S02";  "EDGE" -> "EDGE" + "S02"
    pot_columns: int      # MAXIMUM columns the target reads on a POTENTIALS line
    flag_slots: int       # how many flags CONTROL and PRINT take
    allowed: frozenset    # 4-char keys the target's parser recognises
    ignored: frozenset    # recognised, then discarded with a message by the target
    exe_names: tuple      # candidate executable names; override via env
    verified: bool        # True = checked against source/docs/a real run


# FEFF6L keyword table [SRC] src/feff6l/rdinp.f:834-898.
F6_CARDS = keyset(
    "ATOMS", "HOLE", "OVERLAP", "CONTROL", "EXCHANGE", "ION", "TITLE", "FOLP",
    "RMAX", "DEBYE", "RMULTIPLIER", "SS", "PRINT", "POTENTIALS", "NLEG",
    "REQUIRE", "KLIMIT", "CRITERIA", "NOGEOM", "CSIG", "IORDER", "PCRITERIA",
    "SIG2", "XANES", "CORRECTIONS", "AFOLP", "NEMAX", "INTCALC", "POLARIZATION",
    "ELLIPTICITY", "ISPORB", "END")

# FEFF8.5L keyword table [SRC] src/COMMON/itoken.f:17-140.
F85_CARDS = keyset(
    "ATOMS", "HOLE", "OVERLAP", "CONTROL", "EXCHANGE", "ION", "TITLE", "FOLP",
    "RPATH", "RMAX", "DEBYE", "RMULTIPLIER", "SS", "PRINT", "POTENTIALS", "NLEG",
    "CRITERIA", "NOGEOM", "IORDER", "PCRITERIA", "SIG2", "XANES", "CORRECTIONS",
    "AFOLP", "EXAFS", "POLARIZATION", "ELLIPTICITY", "RGRID", "RPHASES",
    "NSTAR", "NOHOLE", "SIG3", "JUMPRM", "MBCONV", "SPIN", "EDGE", "SCF", "FMS",
    "LDOS", "INTERSTITIAL", "CFAVERAGE", "S02", "XES", "DANES", "FPRIME",
    "RSIGMA", "XNCD", "XMCD", "MULTIPOLE", "UNFREEZEF", "TDLDA", "PMBSE",
    "PLASMON", "SO2CONV", "SELF", "SFSE", "RCONV", "ELNES", "EXELFS", "MAGIC",
    "ABSOLUTE", "EGRID", "END")

# Cards FEFF8.5L parses and then throws away with "... is not available in this
# version of FEFF8.5" [SRC] src/RDINP/rdinp_l.f:402,526,530,552,556,562,574,588,
# 593,620,625,630,641.  Execution continues.
F85_IGNORED = keyset("XANES", "FMS", "LDOS", "XES", "DANES", "FPRIME", "XMCD",
                     "XNCD", "TDLDA", "PMBSE", "ELNES", "EXELFS", "MAGIC", "EGRID")

# [ASSUMED] for the monolithic FEFF8.2/8.4 and for FEFF9/10: no source, no
# executable, no manual was consulted.  Starting point only - do not trust.
F8_CARDS = F85_CARDS
F9_CARDS = F85_CARDS | keyset("RIXS", "COREHOLE")

PROFILES = {
    "feff6":   Profile("feff6",   "HOLE", 3, 4, F6_CARDS,  frozenset(),
                       ("feff6l", "feff6"), True),
    "feff8":   Profile("feff8",   "EDGE", 7, 6, F8_CARDS,  frozenset(),
                       ("feff8", "feff84", "feff82"), False),
    "feff85l": Profile("feff85l", "EDGE", 7, 6, F85_CARDS, F85_IGNORED,
                       ("feff8l", "feff85l"), True),
    "feff9":   Profile("feff9",   "EDGE", 7, 6, F9_CARDS,  frozenset(),
                       ("feff9", "feff"), False),
    "feff10":  Profile("feff10",  "EDGE", 7, 6, F9_CARDS,  frozenset(),
                       ("feff10", "feff"), False),
}

# CONTROL / PRINT flag meanings.  The two layouts are NOT the same list with
# entries added - the four FEFF6 flags do not line up with the first four
# FEFF8 flags, so a card copied across unchanged silently means something else.
#   FEFF6  CONTROL potph paths genfmt ff2chi   [DOC] feff6l_doc.txt:396-405
#                                              [SRC] src/feff6l/rdinp.f:216-223
#   FEFF8  CONTROL mpot mphase mfms mpath mfeff mchi
#                                              [SRC] src/RDINP/rdinp_l.f:201-219
#   FEFF6  PRINT   potph paths genfmt ff2chi   [DOC] feff6l_doc.txt:477-506
#   FEFF8  PRINT   pot xsph fms pathfinder genfmt ff2x
#                                              [SRC] src/RDINP/rdinp_l.f:318-364
# FEFF8L reads a 4-flag card as a FEFF7 card (flag 1 is copied into mpot,
# mphase and mfms) instead of rejecting it [SRC] rdinp_l.f:204-210, 350-356.

SCF_FMS = keyset("SCF", "FMS", "LDOS", "XANES", "COREHOLE")


# ---------------------------------------------------------------- data model
@dataclass
class FeffInput:
    cards: dict = field(default_factory=dict)       # 4-char key -> list[str] of arg lines
    spelling: dict = field(default_factory=dict)    # 4-char key -> card as written
    order: list = field(default_factory=list)       # card order as read
    potentials: list = field(default_factory=list)  # token lists: ipot Z [label lmaxsc lmaxph stoich spin]
    atoms: list = field(default_factory=list)       # token lists: x y z ipot [tag dist]
    warnings: list = field(default_factory=list)

# A comment runs to end of line after any of * % # ; - a line starting with one
# is a comment [SRC] src/COMMON/str.f:192-198, src/feff6l/rdinp.f:825-833.
COMMENT_RE = re.compile(r"[*%#;]")
CARD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def parse(text: str) -> FeffInput:
    fi, section = FeffInput(), None
    for raw in text.splitlines():
        line = COMMENT_RE.split(raw, maxsplit=1)[0].strip()
        if not line:
            continue
        tok = line.split()
        if CARD_RE.match(tok[0]):                   # alphabetic first token = new card
            section = key(tok[0])
            fi.spelling.setdefault(section, tok[0].upper())
            if section not in ("POTE", "ATOM"):
                fi.cards.setdefault(section, []).append(" ".join(tok[1:]))
            fi.order.append(section)
            continue
        if section == "POTE":
            fi.potentials.append(tok)
        elif section == "ATOM":
            fi.atoms.append(tok)
        elif section:                               # multi-line card body
            fi.cards[section].append(line)
    return fi


# ---------------------------------------------------------------- flag cards
def _ints(args: str) -> list:
    out = []
    for t in args.split():
        try:
            out.append(int(t))
        except ValueError:
            break
    return out


def translate_flags(card: str, args: str, dst_slots: int, warn: list) -> str | None:
    """Rewrite a CONTROL or PRINT argument list for a different flag layout."""
    f = _ints(args)
    if not f:
        warn.append(f"{card}: could not read flags from {args!r}; card dropped")
        return None
    if len(f) not in (4, 6):
        warn.append(f"{card}: {len(f)} flags given, expected 4 or 6; passed through "
                    "unchanged and the target will almost certainly abort")
        return args
    src_slots = len(f)
    if src_slots == dst_slots:
        return " ".join(str(x) for x in f)

    if src_slots == 4 and dst_slots == 6:
        if card == "CONTROL":
            potph, paths, genfmt, ff2chi = f
            # FMS does not exist in the EXAFS-only FEFF8.5L build
            # [SRC] src/RDINP/rdinp_l.f:523-528.
            warn.append("CONTROL: FEFF6 potph covers what FEFF8 splits into mpot "
                        "and mphase; both set to the FEFF6 value, mfms set to 0")
            return f"{potph} {potph} 0 {paths} {genfmt} {ff2chi}"
        potph, paths, genfmt, ff2chi = f
        # FEFF6 genfmt writes feffNNNN.dat [DOC] feff6l_doc.txt:498-500; in
        # FEFF8.5L they come from ff2x at ipr6 >= 3 [SRC] rdinp_l.f:341-347,
        # confirmed [RUN]: ipr6=0 gives feff.pad and no feffNNNN.dat at all.
        warn.append("PRINT: FEFF8 ff2x print level set to 3 so that feffNNNN.dat "
                    "files are written; FEFF6 gets them from genfmt instead")
        return f"{potph} 0 0 {paths} {genfmt} 3"

    if src_slots == 6 and dst_slots == 4:
        if card == "CONTROL":
            mpot, mphase, mfms, mpath, mfeff, mchi = f
            if mpot != mphase:
                warn.append(f"CONTROL: mpot={mpot} and mphase={mphase} differ; FEFF6 "
                            f"has one flag for both and gets {mpot}")
            if mfms:
                warn.append("CONTROL: mfms dropped; FEFF6 has no FMS module")
            return f"{mpot} {mpath} {mfeff} {mchi}"
        ipr1, ipr2, ipr3, ipr4, ipr5, ipr6 = f
        if ipr2 or ipr3:
            warn.append(f"PRINT: xsph={ipr2} and fms={ipr3} dropped; FEFF6 has no "
                        "print flag for either")
        if ipr6 > 2:
            warn.append(f"PRINT: ff2x level {ipr6} clamped to 2; FEFF6 ff2chi only "
                        "defines 0, 1 and 2, and writes feffNNNN.dat from genfmt")
            ipr6 = 2
        return f"{ipr1} {ipr4} {ipr5} {ipr6}"
    return args


# ---------------------------------------------------------------- conversion
def convert(fi: FeffInput, target: str, mode: str = "compatible") -> str:
    p, out = PROFILES[target], []
    fi.warnings = []
    warn = fi.warnings

    if not p.verified:
        warn.append(f"{p.name} profile is ASSUMED: its card list and flag layout "
                    "were never checked against that version")

    # Edge / S02: normalise to the target's style.
    hole, s02 = None, None
    if "HOLE" in fi.cards:
        a = fi.cards["HOLE"][0].split()
        hole, s02 = a[0], (a[1] if len(a) > 1 else None)
    if "EDGE" in fi.cards:
        hole = hole or {"K": "1", "L1": "2", "L2": "3", "L3": "4"}.get(
            fi.cards["EDGE"][0].split()[0].upper())
    if "S02" in fi.cards:
        s02 = fi.cards["S02"][0].split()[0]
    if hole is None:
        warn.append("No edge/hole found; defaulting to K (1). Check this.")
        hole = "1"
    if s02 is None:
        # Both versions default S02 to 1 [DOC] feff6l_doc.txt:443-446,
        # [SRC] src/RDINP/rdinp_l.f:74.
        warn.append("No S02 found; using 1.0. Fitted S02 does not transfer "
                    "between versions anyway - refit after converting.")
        s02 = "1.0"

    out.append(f"* Converted by feff_convert.py -> {p.name} ({mode} mode)")
    for t in fi.cards.get("TITL", []):
        out.append(f"TITLE {t}")
    if p.edge_style == "HOLE":
        # FEFF6 hole codes stop at 4 (L3) [DOC] feff6l_doc.txt:450-456.
        if hole not in ("0", "1", "2", "3", "4"):
            warn.append(f"Hole code {hole} has no FEFF6 equivalent (FEFF6 defines "
                        "0-4 only); written through unchanged")
        out.append(f"HOLE {hole} {s02}")
    else:
        edge_name = {"1": "K", "2": "L1", "3": "L2", "4": "L3"}.get(hole, hole)
        out += [f"EDGE {edge_name}", f"S02 {s02}"]

    # Remaining cards.
    skip = keyset("TITLE", "HOLE", "EDGE", "S02", "POTENTIALS", "ATOMS", "END")
    for card in dict.fromkeys(fi.order):            # unique, original order
        if card in skip:
            continue
        name = fi.spelling.get(card, card)
        if card not in p.allowed:
            warn.append(f"DROPPED card {name}: not in {p.name}'s keyword table")
            continue
        if card in p.ignored:
            warn.append(f"KEPT card {name}, but {p.name} parses it and then "
                        "discards it with a message")
        if mode == "compatible" and card in SCF_FMS and p.name != "feff6":
            warn.append(f"DROPPED card {name}: compatible mode keeps a FEFF6-like model")
            continue
        for args in fi.cards[card]:
            if card in ("CONT", "PRIN"):
                args = translate_flags(name, args, p.flag_slots, warn)
                if args is None:
                    continue
            out.append(f"{name} {args}".rstrip())

    if mode == "compatible" and p.name != "feff6":
        if "EXCH" not in fi.cards and p.name == "feff85l":
            # ixc=0 (Hedin-Lundqvist) is the default in both, but pin it so the
            # result does not depend on a default [SRC] src/feff6l/rdinp.f:61,
            # src/RDINP/iniall.f:41.
            out.append("EXCHANGE 0 0 0")
            warn.append("Compatible mode: wrote EXCHANGE 0 0 0 (Hedin-Lundqvist) "
                        "to pin the exchange model instead of relying on a default")
        if p.name == "feff85l":
            # FEFF8.5L overlaps every muffin tin by 15% unless a FOLP card is
            # present [SRC] src/RDINP/rdinp_l.f:70,1046,1059-1063; FEFF6 uses 1.0
            # [SRC] src/feff6l/rdinp.f:128.  Observed [RUN] on fcc Cu: absorber
            # Rmt 1.451 vs 1.293 bohr.
            warn.append("Compatible mode: FEFF8.5L applies AFOLP folp=1.15 by "
                        "default while FEFF6 uses 1.0, so muffin-tin radii still "
                        "differ; add FOLP <ipot> 1.0 per potential to match FEFF6")
        if p.name != "feff85l":
            warn.append("Compatible mode: pin EXCHANGE and the core-hole treatment "
                        "by hand for this version; its card syntax is unverified")

    # POTENTIALS.  Columns past the second are optional in both versions
    # [DOC] feff6l_doc.txt:468-475, [SRC] src/RDINP/rdinp_l.f:703-741, so a
    # missing column is never filled in: a placeholder stoichiometry switches
    # FEFF8.5L from counting atoms to trusting the card (lxnat, rdinp_l.f:737,
    # 935-960) and shifts the potentials.  Observed [RUN] on fcc Cu: writing
    # "1" for the stoichiometry moved Mu from -3.733 to -4.173 eV.
    out.append("POTENTIALS")
    for t in fi.potentials:
        if len(t) > p.pot_columns:
            warn.append(f"ipot {t[0]}: dropped POTENTIALS columns "
                        f"{' '.join(t[p.pot_columns:])}; {p.name} reads "
                        f"{p.pot_columns} at most")
        out.append("  " + " ".join(t[:p.pot_columns]))

    # ATOMS: x y z ipot, plus an optional tag both parsers ignore
    # [SRC] src/RDINP/rdinp_l.f:672-677, src/feff6l/rdinp.f:455-462.
    out.append("ATOMS")
    for a in fi.atoms:
        out.append("  " + " ".join(a[:5]))
    out.append("END")

    for i, w in enumerate(warn):                    # provenance inside the file
        out.insert(1 + i, f"* WARNING: {w}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- running
def find_exe(target: str) -> str | None:
    env = os.environ.get(f"FEFF_EXE_{target.upper()}")
    if env and shutil.which(env):
        return shutil.which(env)
    for name in PROFILES[target].exe_names:
        if shutil.which(name):
            return shutil.which(name)
    return None


# Both wrappers can finish with status 0 after RDINP has aborted, so the log has
# to be checked as well.  Observed [RUN]: feff8l returned 0 on a bad CONTROL card.
FAILED_RE = re.compile(r"fatal error|#ERROR STOP|RDINP fatal|Error reading input|"
                       r"par_stop|Unknown keyword", re.I)


def run(target: str, inp_text: str, workdir: Path | None = None) -> Path:
    exe = find_exe(target)
    if exe is None:
        raise FileNotFoundError(
            f"No {target} executable found. Set FEFF_EXE_{target.upper()} to your "
            f"installed copy. FEFF9/10 require your own license; this tool never ships them.")
    wd = Path(workdir or tempfile.mkdtemp(prefix=f"{target}_"))
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "feff.inp").write_text(inp_text)
    r = subprocess.run([exe], cwd=wd, capture_output=True, text=True)
    log = r.stdout + r.stderr
    (wd / "feff_stdout.log").write_text(log)
    if r.returncode != 0:
        raise RuntimeError(f"{target} exited {r.returncode}; see {wd / 'feff_stdout.log'}")
    hit = FAILED_RE.search(log)
    if hit:
        raise RuntimeError(f"{target} exited 0 but its log reports a failure "
                           f"({hit.group(0)!r}); see {wd / 'feff_stdout.log'}")
    return wd


# ---------------------------------------------------------------- path matching
# Real header line, identical in both versions [RUN]:
#    2  12.000   2.5562    2.6412   -5.50118 nleg, deg, reff, rnrmav(bohr), edge
# followed by one line per leg: x y z ipot iz tag.
HDR = re.compile(r"^\s*(\d+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+[\d.eE+-]+\s+"
                 r"[\d.eE+-]+\s+nleg", re.I)
GEOM_RE = re.compile(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\s+(\d+)")


def read_path(fname: Path) -> tuple | None:
    """Physical signature of one feffNNNN.dat.  Never match paths by index.

    (reff, nleg, degeneracy) is not enough: fcc Cu gives three distinct 4-leg
    paths at reff 5.112 with degeneracy 12, so 22 files collapse to 17
    signatures [RUN].  The scatterer coordinates are unique but not portable -
    the two pathfinders pick different symmetry-equivalent representatives of
    the same path, and only 7 of 22 then match across versions [RUN].  What
    survives both is the shape: walking the path from the absorber, the
    potential index, leg length and scattering angle at each vertex, taken in
    whichever traversal direction sorts first.  That is unique inside each
    version (22/22 and 20/20) and matches 18 paths across the two [RUN].
    """
    lines = Path(fname).read_text(errors="replace").splitlines()
    for i, line in enumerate(lines):
        m = HDR.match(line)
        if not m:
            continue
        nleg, deg, reff = int(m.group(1)), float(m.group(2)), float(m.group(3))
        pts, ipots = [], []
        for g in lines[i + 2: i + 2 + nleg]:
            gm = GEOM_RE.match(g)
            if not gm:
                break
            pts.append([float(gm.group(j)) for j in (1, 2, 3)])
            ipots.append(int(gm.group(4)))
        return (round(reff, 3), nleg, round(deg, 3), _shape(pts, ipots))
    return None


def _shape(pts: list, ipots: list) -> tuple:
    """Absorber-anchored (ipot, leg, angle) sequence, direction-canonical."""
    n = len(pts)
    if n < 2:
        return ()

    def walk(order):
        p = [pts[k] for k in order]
        q = [ipots[k] for k in order]
        out = []
        for k in range(n):
            leg = math.dist(p[k], p[(k + 1) % n])
            a, b, c = p[k - 1], p[k], p[(k + 1) % n]
            u = [a[j] - b[j] for j in range(3)]
            v = [c[j] - b[j] for j in range(3)]
            denom = math.dist(a, b) * math.dist(b, c)
            cosv = sum(u[j] * v[j] for j in range(3)) / denom if denom else 0.0
            ang = math.degrees(math.acos(max(-1.0, min(1.0, cosv))))
            out.append((q[k], round(leg, 3), round(ang, 1)))
        return tuple(out)

    return min(walk(list(range(n))), walk([0] + list(range(n - 1, 0, -1))))


def path_signatures(workdir: Path) -> set:
    sigs = set()
    for f in sorted(Path(workdir).glob("feff[0-9][0-9][0-9][0-9].dat")):
        sig = read_path(f)
        if sig is not None:
            sigs.add(sig)
    return sigs


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--to", required=True, choices=PROFILES)
    ap.add_argument("--mode", default="compatible", choices=["compatible", "native"])
    ap.add_argument("-o", "--output", type=Path, default=Path("feff_converted.inp"))
    ap.add_argument("--run", action="store_true", help="run the target executable if found")
    a = ap.parse_args()
    fi = parse(a.input.read_text())
    text = convert(fi, a.to, a.mode)
    a.output.write_text(text)
    for w in fi.warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    if a.run:
        wd = run(a.to, text)
        print(f"ran in {wd}; {len(path_signatures(wd))} path signatures")


if __name__ == "__main__":
    main()
