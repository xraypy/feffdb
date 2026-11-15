"""Unit tests for feff_convert.py - no FEFF executable needed."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feff_convert as fc  # noqa: E402

INPUTS = Path(__file__).parent / "inputs"

MINIMAL = """\
TITLE two atom test
HOLE 1 0.85
CONTROL 1 1 1 1
PRINT 1 0 0 0
RMAX 6.0
POTENTIALS
  0 29 Cu
  1 8  O
ATOMS
  0.0 0.0 0.0 0 Cu
  0.0 0.0 1.9 1 O
END
"""


def warnings_for(text, target, mode="compatible"):
    fi = fc.parse(text)
    out = fc.convert(fi, target, mode)
    return out, fi.warnings


# ----------------------------------------------------------------- parsing
def test_parse_keeps_cards_potentials_and_atoms():
    fi = fc.parse(MINIMAL)
    assert fi.cards["HOLE"] == ["1 0.85"]
    assert fi.cards["TITL"] == ["two atom test"]
    assert fi.potentials == [["0", "29", "Cu"], ["1", "8", "O"]]
    assert len(fi.atoms) == 2
    assert fi.atoms[1] == ["0.0", "0.0", "1.9", "1", "O"]


@pytest.mark.parametrize("char", "*%#;")
def test_all_four_comment_characters_are_stripped(char):
    fi = fc.parse(f"{char} a whole comment line\nHOLE 1 1.0 {char} trailing\n")
    assert fi.cards["HOLE"] == ["1 1.0"]


def test_keywords_match_on_their_first_four_characters():
    # FEFF compares word(1:4) only, so POTENTIAL and POTENTIALS are one card.
    fi = fc.parse("POTENTIAL\n  0 29 Cu\nATOM\n  0.0 0.0 0.0 0\n")
    assert fi.potentials == [["0", "29", "Cu"]]
    assert fi.atoms == [["0.0", "0.0", "0.0", "0"]]


# ------------------------------------------------------------ edge and S02
def test_hole_becomes_edge_plus_s02_going_up():
    out, _ = warnings_for(MINIMAL, "feff85l")
    assert "EDGE K" in out
    assert "S02 0.85" in out
    assert "HOLE" not in out


def test_edge_plus_s02_becomes_hole_going_down():
    src = MINIMAL.replace("HOLE 1 0.85", "EDGE K\nS02 0.85")
    out, _ = warnings_for(src, "feff6")
    assert "HOLE 1 0.85" in out
    assert "\nEDGE" not in out


def test_missing_s02_warns_about_refitting():
    out, warn = warnings_for(MINIMAL.replace("HOLE 1 0.85", "HOLE 1"), "feff6")
    assert "HOLE 1 1.0" in out
    assert any("does not transfer" in w for w in warn)


# -------------------------------------------------------- CONTROL and PRINT
def test_control_four_flags_becomes_six_with_fms_off():
    out, warn = warnings_for(MINIMAL, "feff85l")
    assert "CONTROL 1 1 0 1 1 1" in out
    assert any("mfms set to 0" in w for w in warn)


def test_print_four_flags_asks_ff2x_for_the_path_files():
    # FEFF8.5L writes feffNNNN.dat from ff2x at level 3, not from genfmt.
    out, warn = warnings_for(MINIMAL, "feff85l")
    assert "PRINT 1 0 0 0 0 3" in out
    assert any("feffNNNN.dat" in w for w in warn)


def test_control_six_flags_becomes_four_and_warns_about_fms():
    src = MINIMAL.replace("CONTROL 1 1 1 1", "CONTROL 1 1 1 1 1 1")
    out, warn = warnings_for(src, "feff6")
    assert "CONTROL 1 1 1 1" in out
    assert any("mfms dropped" in w for w in warn)


def test_control_six_flags_warns_when_mpot_and_mphase_disagree():
    src = MINIMAL.replace("CONTROL 1 1 1 1", "CONTROL 0 1 0 1 1 1")
    out, warn = warnings_for(src, "feff6")
    assert "CONTROL 0 1 1 1" in out
    assert any("mphase" in w for w in warn)


def test_print_six_flags_clamps_the_ff2x_level_for_feff6():
    src = MINIMAL.replace("PRINT 1 0 0 0", "PRINT 1 0 0 0 1 3")
    out, warn = warnings_for(src, "feff6")
    assert "PRINT 1 0 1 2" in out
    assert any("clamped to 2" in w for w in warn)


def test_a_flag_card_with_a_strange_count_is_passed_through_with_a_warning():
    src = MINIMAL.replace("CONTROL 1 1 1 1", "CONTROL 1 1 1")
    out, warn = warnings_for(src, "feff85l")
    assert "CONTROL 1 1 1" in out
    assert any("expected 4 or 6" in w for w in warn)


# ------------------------------------------------------------- POTENTIALS
def test_extra_potentials_columns_are_stripped_for_feff6():
    src = MINIMAL.replace("  0 29 Cu", "  0 29 Cu 3 3 1").replace(
        "  1 8  O", "  1 8  O 2 2 6")
    out, warn = warnings_for(src, "feff6")
    assert "  0 29 Cu\n" in out
    assert "  1 8 O\n" in out
    assert sum("dropped POTENTIALS columns" in w for w in warn) == 2


def test_missing_potentials_columns_are_never_invented():
    # Filling in a stoichiometry makes FEFF8.5L trust the card instead of
    # counting atoms, which moves the potentials.
    out, warn = warnings_for(MINIMAL, "feff85l")
    assert "  0 29 Cu\n" in out
    assert "-1" not in out
    assert not any("placeholder" in w for w in warn)


def test_seven_potentials_columns_survive_the_trip_to_feff85l():
    src = MINIMAL.replace("  0 29 Cu", "  0 29 Cu 3 3 1 0")
    out, _ = warnings_for(src, "feff85l")
    assert "  0 29 Cu 3 3 1 0\n" in out


# ------------------------------------------------------------ card filtering
def test_a_card_outside_the_target_table_is_dropped_with_a_warning():
    src = MINIMAL.replace("RMAX 6.0", "RMAX 6.0\nSCF 4.0")
    out, warn = warnings_for(src, "feff6")
    body = [l for l in out.splitlines() if not l.startswith("*")]
    assert not any(l.startswith("SCF") for l in body)
    assert any("not in feff6's keyword table" in w for w in warn)


def test_compatible_mode_drops_scf_for_feff85l_but_native_mode_keeps_it():
    src = MINIMAL.replace("RMAX 6.0", "RMAX 6.0\nSCF 4.0")
    out_c, warn_c = warnings_for(src, "feff85l", "compatible")
    out_n, _ = warnings_for(src, "feff85l", "native")
    assert "\nSCF 4.0" not in out_c
    assert any("FEFF6-like model" in w for w in warn_c)
    assert "\nSCF 4.0" in out_n


def test_a_card_feff85l_accepts_then_discards_is_flagged():
    src = MINIMAL.replace("RMAX 6.0", "RMAX 6.0\nFMS 6.0")
    _, warn = warnings_for(src, "feff85l", "native")
    assert any("discards it" in w for w in warn)


def test_rpath_is_feff8_only():
    src = MINIMAL.replace("RMAX 6.0", "RPATH 6.0")
    out85, _ = warnings_for(src, "feff85l")
    out6, warn6 = warnings_for(src, "feff6")
    assert "RPATH 6.0" in out85
    assert any("RPATH" in w and "not in feff6" in w for w in warn6)
    assert "\nRPATH" not in out6


# ----------------------------------------------------------- warnings, modes
def test_every_warning_is_written_into_the_file_in_order():
    out, warn = warnings_for(MINIMAL, "feff85l")
    written = [l[len("* WARNING: "):] for l in out.splitlines()
               if l.startswith("* WARNING: ")]
    assert written == warn


def test_converting_twice_does_not_stack_up_warnings():
    fi = fc.parse(MINIMAL)
    fc.convert(fi, "feff85l")
    first = list(fi.warnings)
    fc.convert(fi, "feff85l")
    assert fi.warnings == first


def test_an_unverified_profile_says_so():
    _, warn = warnings_for(MINIMAL, "feff9")
    assert any("ASSUMED" in w for w in warn)
    _, warn85 = warnings_for(MINIMAL, "feff85l")
    assert not any("ASSUMED" in w for w in warn85)


def test_converted_output_parses_back_to_the_same_structure():
    out, _ = warnings_for(MINIMAL, "feff85l")
    again = fc.parse(out)
    assert again.potentials == [["0", "29", "Cu"], ["1", "8", "O"]]
    assert len(again.atoms) == 2


def test_the_hand_written_cu_input_converts_both_ways():
    six = (INPUTS / "cu_fcc_feff6.inp").read_text()
    eight = (INPUTS / "cu_fcc_feff85l.inp").read_text()
    up, _ = warnings_for(six, "feff85l")
    down, _ = warnings_for(eight, "feff6")
    assert up.count("\n  ") == six.count("\n  ")      # same atom + ipot count
    assert "EDGE K" in up and "HOLE 1" in down


# -------------------------------------------------------- path file reading
def test_the_header_regex_matches_a_real_feff_dat_line():
    line = ("   2  12.000   2.5562    2.6412   -5.50118 "
            "nleg, deg, reff, rnrmav(bohr), edge")
    m = fc.HDR.match(line)
    assert m and (int(m.group(1)), float(m.group(2)), float(m.group(3))) == (
        2, 12.0, 2.5562)


def test_the_shape_of_a_triangle_does_not_depend_on_the_traversal_direction():
    # Same triangle, same absorber, scatterers visited the other way round.
    absorber = [0.0, 0.0, 0.0]
    s1, s2 = [0.0, 1.8075, 1.8075], [1.8075, 1.8075, 0.0]
    assert fc._shape([absorber, s1, s2], [0, 1, 1]) == \
           fc._shape([absorber, s2, s1], [0, 1, 1])


def test_two_paths_of_the_same_length_and_degeneracy_get_different_shapes():
    absorber = [0.0, 0.0, 0.0]
    a = fc._shape([absorber, [0.0, 1.8075, 1.8075], [1.8075, 1.8075, 0.0]],
                  [0, 1, 1])
    b = fc._shape([absorber, [0.0, 1.8075, 1.8075], [0.0, 3.615, 0.0]],
                  [0, 1, 1])
    assert a != b
