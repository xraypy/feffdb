"""Execution tests - skipped unless feff6l and feff8l are on PATH."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feff_convert as fc  # noqa: E402

INPUTS = Path(__file__).parent / "inputs"

HAVE_F6 = fc.find_exe("feff6") is not None
HAVE_F85 = fc.find_exe("feff85l") is not None
needs_f6 = pytest.mark.skipif(not HAVE_F6, reason="no feff6l executable on PATH")
needs_f85 = pytest.mark.skipif(not HAVE_F85, reason="no feff8l executable on PATH")
needs_both = pytest.mark.skipif(not (HAVE_F6 and HAVE_F85),
                                reason="needs both feff6l and feff8l")


def convert_file(name, target, mode="compatible"):
    return fc.convert(fc.parse((INPUTS / name).read_text()), target, mode)


@pytest.fixture(scope="module")
def run6(tmp_path_factory):
    text = convert_file("cu_fcc_feff85l.inp", "feff6")
    return fc.run("feff6", text, tmp_path_factory.mktemp("f6"))


@pytest.fixture(scope="module")
def run85(tmp_path_factory):
    text = convert_file("cu_fcc_feff6.inp", "feff85l")
    return fc.run("feff85l", text, tmp_path_factory.mktemp("f85"))


@needs_f6
def test_converted_input_runs_in_feff6l_and_writes_path_files(run6):
    assert (run6 / "paths.dat").exists()
    assert len(list(run6.glob("feff[0-9][0-9][0-9][0-9].dat"))) > 10


@needs_f85
def test_converted_input_runs_in_feff85l_and_writes_path_files(run85):
    # Only true because PRINT is rewritten with ff2x level 3.
    assert (run85 / "paths.dat").exists()
    assert (run85 / "chi.dat").exists()
    assert len(list(run85.glob("feff[0-9][0-9][0-9][0-9].dat"))) > 10


@needs_both
def test_path_signatures_are_unique_inside_each_run(run6, run85):
    for wd in (run6, run85):
        files = list(wd.glob("feff[0-9][0-9][0-9][0-9].dat"))
        assert len(fc.path_signatures(wd)) == len(files)


@needs_both
def test_most_paths_are_shared_and_the_indices_are_not(run6, run85):
    a, b = fc.path_signatures(run6), fc.path_signatures(run85)
    assert len(a & b) >= 15
    by6 = {fc.read_path(f): f.name for f in sorted(
        run6.glob("feff[0-9][0-9][0-9][0-9].dat"))}
    by85 = {fc.read_path(f): f.name for f in sorted(
        run85.glob("feff[0-9][0-9][0-9][0-9].dat"))}
    assert any(by6[s] != by85[s] for s in a & b), "path index happened to be stable"


@needs_both
def test_the_first_shell_survives_both_conversions_at_the_same_length(run6, run85):
    def first_shell(wd):
        return min(fc.path_signatures(wd), key=lambda s: s[0])
    assert abs(first_shell(run6)[0] - first_shell(run85)[0]) < 0.001


@needs_f6
def test_a_bad_control_card_is_caught_even_though_feff_exits_zero(tmp_path):
    text = (INPUTS / "cu_fcc_feff6.inp").read_text().replace(
        "CONTROL 1 1 1 1", "CONTROL 1 1 1")
    with pytest.raises(RuntimeError, match="log reports a failure"):
        fc.run("feff6", text, tmp_path / "bad")


@needs_f6
def test_feff6l_rejects_an_edge_card(tmp_path):
    text = (INPUTS / "cu_fcc_feff6.inp").read_text().replace(
        "HOLE 1   1.0", "EDGE K\nS02 1.0")
    with pytest.raises(RuntimeError, match="log reports a failure"):
        fc.run("feff6", text, tmp_path / "edge")


@needs_f85
def test_feff85l_still_accepts_a_feff6_style_hole_card(tmp_path):
    text = (INPUTS / "cu_fcc_feff6.inp").read_text().replace(
        "PRINT   1 0 0 0", "PRINT   1 0 0 0 1 3").replace(
        "CONTROL 1 1 1 1", "CONTROL 1 1 1 1 1 1")
    wd = fc.run("feff85l", text, tmp_path / "hole")
    assert len(list(wd.glob("feff[0-9][0-9][0-9][0-9].dat"))) > 10
