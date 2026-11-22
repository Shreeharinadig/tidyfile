import pytest

from evaluate import evaluate, render_table
from generate import generate


@pytest.fixture(scope="module")
def data_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("bench_eval")
    generate(out, seed=42)
    return out


def test_baseline_reports_all_groups(data_dir):
    result = evaluate(data_dir, "rules")
    stats = result["stats"]
    assert stats["all"]["files"] == 50
    assert stats["split:dev"]["files"] + stats["split:heldout"]["files"] == 50
    assert stats["all"]["header_ok"] == 50


def test_baseline_is_a_floor_not_perfect(data_dir):
    # The LLM mapper needs headroom above the rules, so the baseline must not be perfect.
    stats = evaluate(data_dir, "rules")["stats"]["all"]
    accuracy = stats["target_correct"] / stats["target_columns"]
    assert 0.4 < accuracy < 0.95


def test_rules_never_map_extra_columns(data_dir):
    stats = evaluate(data_dir, "rules")["stats"]["all"]
    assert stats["extra_clean"] == stats["extra_columns"]


def test_table_renders(data_dir):
    table = render_table(evaluate(data_dir, "rules"), "rules")
    assert "split:heldout" in table and "Mapping accuracy" in table
