import json
from collections import Counter

import pytest

from generate import FILES_PER_TYPE, generate
from tidyfile_worker.profiling import find_header_row, read_raw
from tidyfile_worker.schemas import SCHEMAS


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("bench")
    entries = generate(out, seed=42)
    return out, entries


def test_file_counts_and_split(dataset):
    out, entries = dataset
    assert len(entries) == 50
    assert Counter(e["dataset_type"] for e in entries) == Counter(FILES_PER_TYPE)
    assert sum(e["split"] == "heldout" for e in entries) == 15
    assert len(list((out / "inputs").iterdir())) == 50
    assert len(list((out / "expected").iterdir())) == 50


def test_truth_columns_use_valid_targets_without_duplicates(dataset):
    out, entries = dataset
    for entry in entries:
        targets = [c["target"] for c in entry["columns"] if c["target"]]
        assert len(targets) == len(set(targets))
        assert set(targets) <= set(SCHEMAS[entry["dataset_type"]])
        headers = [c["header"].lower() for c in entry["columns"]]
        assert len(headers) == len(set(headers))


def test_header_row_in_truth_matches_the_written_file(dataset):
    out, entries = dataset
    for entry in entries:
        rows = read_raw(out / "inputs" / entry["file"])
        row = rows[entry["header_row"]]
        assert [c for c in row if c] == [c["header"] for c in entry["columns"]]
        assert find_header_row(rows) == entry["header_row"]


def test_same_seed_is_deterministic_and_different_seed_differs(tmp_path):
    a = generate(tmp_path / "a", seed=7)
    b = generate(tmp_path / "b", seed=7)
    c = generate(tmp_path / "c", seed=8)
    fingerprint = lambda root: json.loads((root / "manifest.json").read_text())["fingerprint"]
    assert fingerprint(tmp_path / "a") == fingerprint(tmp_path / "b")
    assert fingerprint(tmp_path / "a") != fingerprint(tmp_path / "c")
    assert a == b


def test_expected_row_counts_match_truth(dataset):
    out, entries = dataset
    for entry in entries:
        stem = entry["file"].rsplit(".", 1)[0]
        lines = (out / "expected" / f"{stem}.csv").read_text().strip().splitlines()
        assert len(lines) - 1 == entry["expected_rows"]
