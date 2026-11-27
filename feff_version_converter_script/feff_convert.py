#!/usr/bin/env python3
import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def card_key(card_name):
    return card_name.upper()[:4]


def card_keys(*card_names):
    return frozenset(card_key(name) for name in card_names)


@dataclass
class VersionProfile:
    name: str
    edge_card_style: str
    potentials_columns_read: int
    control_and_print_slots: int
    cards_the_parser_accepts: frozenset
    cards_accepted_then_discarded: frozenset
    executable_names: tuple
    profile_was_verified: bool


FEFF6_CARDS = card_keys(
    "ATOMS", "HOLE", "OVERLAP", "CONTROL", "EXCHANGE", "ION", "TITLE", "FOLP",
    "RMAX", "DEBYE", "RMULTIPLIER", "SS", "PRINT", "POTENTIALS", "NLEG",
    "REQUIRE", "KLIMIT", "CRITERIA", "NOGEOM", "CSIG", "IORDER", "PCRITERIA",
    "SIG2", "XANES", "CORRECTIONS", "AFOLP", "NEMAX", "INTCALC", "POLARIZATION",
    "ELLIPTICITY", "ISPORB", "END")

FEFF85L_CARDS = card_keys(
    "ATOMS", "HOLE", "OVERLAP", "CONTROL", "EXCHANGE", "ION", "TITLE", "FOLP",
    "RPATH", "RMAX", "DEBYE", "RMULTIPLIER", "SS", "PRINT", "POTENTIALS", "NLEG",
    "CRITERIA", "NOGEOM", "IORDER", "PCRITERIA", "SIG2", "XANES", "CORRECTIONS",
    "AFOLP", "EXAFS", "POLARIZATION", "ELLIPTICITY", "RGRID", "RPHASES",
    "NSTAR", "NOHOLE", "SIG3", "JUMPRM", "MBCONV", "SPIN", "EDGE", "SCF", "FMS",
    "LDOS", "INTERSTITIAL", "CFAVERAGE", "S02", "XES", "DANES", "FPRIME",
    "RSIGMA", "XNCD", "XMCD", "MULTIPOLE", "UNFREEZEF", "TDLDA", "PMBSE",
    "PLASMON", "SO2CONV", "SELF", "SFSE", "RCONV", "ELNES", "EXELFS", "MAGIC",
    "ABSOLUTE", "EGRID", "END")

FEFF85L_CARDS_ACCEPTED_THEN_DISCARDED = card_keys(
    "XANES", "FMS", "LDOS", "XES", "DANES", "FPRIME", "XMCD", "XNCD", "TDLDA",
    "PMBSE", "ELNES", "EXELFS", "MAGIC", "EGRID")

FEFF8_CARDS = FEFF85L_CARDS
FEFF9_CARDS = FEFF85L_CARDS | card_keys("RIXS", "COREHOLE")

CARDS_BEYOND_THE_FEFF6_MODEL = card_keys("SCF", "FMS", "LDOS", "XANES", "COREHOLE")

EDGE_NAME_TO_HOLE_CODE = {"K": "1", "L1": "2", "L2": "3", "L3": "4"}
HOLE_CODE_TO_EDGE_NAME = {"1": "K", "2": "L1", "3": "L2", "4": "L3"}

VERSION_PROFILES = {
    "feff6": VersionProfile(
        "feff6", "HOLE", 3, 4, FEFF6_CARDS, frozenset(), ("feff6l", "feff6"), True),
    "feff8": VersionProfile(
        "feff8", "EDGE", 7, 6, FEFF8_CARDS, frozenset(),
        ("feff8", "feff84", "feff82"), False),
    "feff85l": VersionProfile(
        "feff85l", "EDGE", 7, 6, FEFF85L_CARDS, FEFF85L_CARDS_ACCEPTED_THEN_DISCARDED,
        ("feff8l", "feff85l"), True),
    "feff9": VersionProfile(
        "feff9", "EDGE", 7, 6, FEFF9_CARDS, frozenset(), ("feff9", "feff"), False),
    "feff10": VersionProfile(
        "feff10", "EDGE", 7, 6, FEFF9_CARDS, frozenset(), ("feff10", "feff"), False),
}


@dataclass
class ParsedFeffInput:
    card_arguments: dict = field(default_factory=dict)
    card_spelling_as_written: dict = field(default_factory=dict)
    card_order: list = field(default_factory=list)
    potentials: list = field(default_factory=list)
    atoms: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


COMMENT_CHARACTER = re.compile(r"[*%#;]")
CARD_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def parse_feff_input(text):
    parsed = ParsedFeffInput()
    current_card = None
    for raw_line in text.splitlines():
        line = COMMENT_CHARACTER.split(raw_line, maxsplit=1)[0].strip()
        if not line:
            continue
        words = line.split()
        if CARD_NAME.match(words[0]):
            current_card = card_key(words[0])
            parsed.card_spelling_as_written.setdefault(current_card, words[0].upper())
            if current_card not in ("POTE", "ATOM"):
                parsed.card_arguments.setdefault(current_card, []).append(
                    " ".join(words[1:]))
            parsed.card_order.append(current_card)
        elif current_card == "POTE":
            parsed.potentials.append(words)
        elif current_card == "ATOM":
            parsed.atoms.append(words)
        elif current_card:
            parsed.card_arguments[current_card].append(line)
    return parsed


def leading_integers(text):
    numbers = []
    for word in text.split():
        try:
            numbers.append(int(word))
        except ValueError:
            break
    return numbers


def translate_control_or_print_flags(card_name, arguments, slots_in_target, warnings):
    flags = leading_integers(arguments)
    if not flags:
        warnings.append(
            f"{card_name}: could not read flags from {arguments!r}; card dropped")
        return None
    if len(flags) not in (4, 6):
        warnings.append(
            f"{card_name}: {len(flags)} flags given, expected 4 or 6; passed through "
            "unchanged and the target will almost certainly abort")
        return arguments
    if len(flags) == slots_in_target:
        return " ".join(str(flag) for flag in flags)

    is_control_card = card_key(card_name) == "CONT"

    if len(flags) == 4 and slots_in_target == 6:
        potph, paths, genfmt, ff2chi = flags
        if is_control_card:
            warnings.append(
                "CONTROL: FEFF6 potph covers what FEFF8 splits into mpot and mphase; "
                "both set to the FEFF6 value, mfms set to 0")
            return f"{potph} {potph} 0 {paths} {genfmt} {ff2chi}"
        warnings.append(
            "PRINT: FEFF8 ff2x print level set to 3 so that feffNNNN.dat files are "
            "written; FEFF6 gets them from genfmt instead")
        return f"{potph} 0 0 {paths} {genfmt} 3"

    if len(flags) == 6 and slots_in_target == 4:
        if is_control_card:
            mpot, mphase, mfms, mpath, mfeff, mchi = flags
            if mpot != mphase:
                warnings.append(
                    f"CONTROL: mpot={mpot} and mphase={mphase} differ; FEFF6 has one "
                    f"flag for both and gets {mpot}")
            if mfms:
                warnings.append("CONTROL: mfms dropped; FEFF6 has no FMS module")
            return f"{mpot} {mpath} {mfeff} {mchi}"
        pot, xsph, fms, pathfinder, genfmt, ff2x = flags
        if xsph or fms:
            warnings.append(
                f"PRINT: xsph={xsph} and fms={fms} dropped; FEFF6 has no print flag "
                "for either")
        if ff2x > 2:
            warnings.append(
                f"PRINT: ff2x level {ff2x} clamped to 2; FEFF6 ff2chi only defines "
                "0, 1 and 2, and writes feffNNNN.dat from genfmt")
            ff2x = 2
        return f"{pot} {pathfinder} {genfmt} {ff2x}"

    return arguments


def convert_to_version(parsed, target_version, mode="compatible"):
    profile = VERSION_PROFILES[target_version]
    parsed.warnings = []
    warnings = parsed.warnings
    lines = []

    if not profile.profile_was_verified:
        warnings.append(
            f"{profile.name} profile is ASSUMED: its card list and flag layout were "
            "never checked against that version")

    hole_code = None
    amplitude_reduction_factor = None
    if "HOLE" in parsed.card_arguments:
        hole_words = parsed.card_arguments["HOLE"][0].split()
        hole_code = hole_words[0]
        if len(hole_words) > 1:
            amplitude_reduction_factor = hole_words[1]
    if "EDGE" in parsed.card_arguments and hole_code is None:
        edge_name = parsed.card_arguments["EDGE"][0].split()[0].upper()
        hole_code = EDGE_NAME_TO_HOLE_CODE.get(edge_name)
    if "S02" in parsed.card_arguments:
        amplitude_reduction_factor = parsed.card_arguments["S02"][0].split()[0]
    if hole_code is None:
        warnings.append("No edge/hole found; defaulting to K (1). Check this.")
        hole_code = "1"
    if amplitude_reduction_factor is None:
        warnings.append(
            "No S02 found; using 1.0. Fitted S02 does not transfer between versions "
            "anyway - refit after converting.")
        amplitude_reduction_factor = "1.0"

    lines.append(f"* Converted by feff_convert.py -> {profile.name} ({mode} mode)")
    for title in parsed.card_arguments.get("TITL", []):
        lines.append(f"TITLE {title}")
    if profile.edge_card_style == "HOLE":
        if hole_code not in ("0", "1", "2", "3", "4"):
            warnings.append(
                f"Hole code {hole_code} has no FEFF6 equivalent (FEFF6 defines 0-4 "
                "only); written through unchanged")
        lines.append(f"HOLE {hole_code} {amplitude_reduction_factor}")
    else:
        lines.append(f"EDGE {HOLE_CODE_TO_EDGE_NAME.get(hole_code, hole_code)}")
        lines.append(f"S02 {amplitude_reduction_factor}")

    cards_already_written = card_keys(
        "TITLE", "HOLE", "EDGE", "S02", "POTENTIALS", "ATOMS", "END")
    for card in dict.fromkeys(parsed.card_order):
        if card in cards_already_written:
            continue
        name_as_written = parsed.card_spelling_as_written.get(card, card)
        if card not in profile.cards_the_parser_accepts:
            warnings.append(
                f"DROPPED card {name_as_written}: not in {profile.name}'s keyword table")
            continue
        if card in profile.cards_accepted_then_discarded:
            warnings.append(
                f"KEPT card {name_as_written}, but {profile.name} parses it and then "
                "discards it with a message")
        if (mode == "compatible" and card in CARDS_BEYOND_THE_FEFF6_MODEL
                and profile.name != "feff6"):
            warnings.append(
                f"DROPPED card {name_as_written}: compatible mode keeps a FEFF6-like model")
            continue
        for arguments in parsed.card_arguments[card]:
            if card in ("CONT", "PRIN"):
                arguments = translate_control_or_print_flags(
                    name_as_written, arguments, profile.control_and_print_slots, warnings)
                if arguments is None:
                    continue
            lines.append(f"{name_as_written} {arguments}".rstrip())

    if mode == "compatible" and profile.name != "feff6":
        if profile.name == "feff85l":
            if "EXCH" not in parsed.card_arguments:
                lines.append("EXCHANGE 0 0 0")
                warnings.append(
                    "Compatible mode: wrote EXCHANGE 0 0 0 (Hedin-Lundqvist) to pin "
                    "the exchange model instead of relying on a default")
            warnings.append(
                "Compatible mode: FEFF8.5L applies AFOLP folp=1.15 by default while "
                "FEFF6 uses 1.0, so muffin-tin radii still differ; add FOLP <ipot> 1.0 "
                "per potential to match FEFF6")
        else:
            warnings.append(
                "Compatible mode: pin EXCHANGE and the core-hole treatment by hand for "
                "this version; its card syntax is unverified")

    lines.append("POTENTIALS")
    for potential in parsed.potentials:
        if len(potential) > profile.potentials_columns_read:
            warnings.append(
                f"ipot {potential[0]}: dropped POTENTIALS columns "
                f"{' '.join(potential[profile.potentials_columns_read:])}; "
                f"{profile.name} reads {profile.potentials_columns_read} at most")
        lines.append("  " + " ".join(potential[:profile.potentials_columns_read]))

    lines.append("ATOMS")
    for atom in parsed.atoms:
        lines.append("  " + " ".join(atom[:5]))
    lines.append("END")

    for position, warning in enumerate(warnings):
        lines.insert(1 + position, f"* WARNING: {warning}")
    return "\n".join(lines) + "\n"


def find_feff_executable(target_version):
    from_environment = os.environ.get(f"FEFF_EXE_{target_version.upper()}")
    if from_environment and shutil.which(from_environment):
        return shutil.which(from_environment)
    for name in VERSION_PROFILES[target_version].executable_names:
        if shutil.which(name):
            return shutil.which(name)
    return None


FAILURE_IN_LOG = re.compile(
    r"fatal error|#ERROR STOP|RDINP fatal|Error reading input|par_stop|Unknown keyword",
    re.I)


def run_feff(target_version, input_text, working_directory=None):
    executable = find_feff_executable(target_version)
    if executable is None:
        raise FileNotFoundError(
            f"No {target_version} executable found. Set FEFF_EXE_{target_version.upper()} "
            "to your installed copy. FEFF9/10 require your own license; this tool never "
            "ships them.")
    directory = Path(working_directory or tempfile.mkdtemp(prefix=f"{target_version}_"))
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "feff.inp").write_text(input_text)
    finished = subprocess.run([executable], cwd=directory, capture_output=True, text=True)
    log_text = finished.stdout + finished.stderr
    log_file = directory / "feff_stdout.log"
    log_file.write_text(log_text)
    if finished.returncode != 0:
        raise RuntimeError(f"{target_version} exited {finished.returncode}; see {log_file}")
    failure = FAILURE_IN_LOG.search(log_text)
    if failure:
        raise RuntimeError(
            f"{target_version} exited 0 but its log reports a failure "
            f"({failure.group(0)!r}); see {log_file}")
    return directory


PATH_HEADER = re.compile(
    r"^\s*(\d+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+[\d.eE+-]+\s+[\d.eE+-]+\s+nleg", re.I)
PATH_LEG = re.compile(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(\d+)\s+(\d+)")


def read_path_signature(path_file):
    lines = Path(path_file).read_text(errors="replace").splitlines()
    for line_number, line in enumerate(lines):
        header = PATH_HEADER.match(line)
        if not header:
            continue
        number_of_legs = int(header.group(1))
        degeneracy = float(header.group(2))
        half_path_length = float(header.group(3))
        points = []
        potential_indices = []
        for leg_line in lines[line_number + 2: line_number + 2 + number_of_legs]:
            leg = PATH_LEG.match(leg_line)
            if not leg:
                break
            points.append([float(leg.group(axis)) for axis in (1, 2, 3)])
            potential_indices.append(int(leg.group(4)))
        return (round(half_path_length, 3), number_of_legs, round(degeneracy, 3),
                path_shape(points, potential_indices))
    return None


def path_shape(points, potential_indices):
    number_of_vertices = len(points)
    if number_of_vertices < 2:
        return ()

    def shape_walking(visit_order):
        walk_points = [points[i] for i in visit_order]
        walk_potentials = [potential_indices[i] for i in visit_order]
        vertices = []
        for i in range(number_of_vertices):
            previous_point = walk_points[i - 1]
            this_point = walk_points[i]
            next_point = walk_points[(i + 1) % number_of_vertices]
            leg_length = math.dist(this_point, next_point)
            to_previous = [previous_point[axis] - this_point[axis] for axis in range(3)]
            to_next = [next_point[axis] - this_point[axis] for axis in range(3)]
            length_product = (math.dist(previous_point, this_point)
                              * math.dist(this_point, next_point))
            if length_product:
                cosine = sum(to_previous[axis] * to_next[axis]
                             for axis in range(3)) / length_product
            else:
                cosine = 0.0
            angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
            vertices.append((walk_potentials[i], round(leg_length, 3), round(angle, 1)))
        return tuple(vertices)

    forwards = list(range(number_of_vertices))
    backwards = [0] + list(range(number_of_vertices - 1, 0, -1))
    return min(shape_walking(forwards), shape_walking(backwards))


def all_path_signatures(directory):
    signatures = set()
    for path_file in sorted(Path(directory).glob("feff[0-9][0-9][0-9][0-9].dat")):
        signature = read_path_signature(path_file)
        if signature is not None:
            signatures.add(signature)
    return signatures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--to", required=True, choices=VERSION_PROFILES)
    parser.add_argument("--mode", default="compatible", choices=["compatible", "native"])
    parser.add_argument("-o", "--output", type=Path, default=Path("feff_converted.inp"))
    parser.add_argument("--run", action="store_true")
    options = parser.parse_args()
    parsed = parse_feff_input(options.input.read_text())
    converted_text = convert_to_version(parsed, options.to, options.mode)
    options.output.write_text(converted_text)
    for warning in parsed.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if options.run:
        directory = run_feff(options.to, converted_text)
        print(f"ran in {directory}; {len(all_path_signatures(directory))} path signatures")


if __name__ == "__main__":
    main()
