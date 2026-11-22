"""Evaluate a column mapper against the benchmark ground truth.

Usage:
    PYTHONPATH=worker:benchmark python3 benchmark/evaluate.py --mapper rules
    PYTHONPATH=worker:benchmark python3 benchmark/evaluate.py --show-errors

Writes a results table to benchmark/results/latest.md. Prompt tuning must only
ever look at the "dev" split; the "heldout" split is for the final number.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from tidyfile_worker.mapping import map_columns
from tidyfile_worker.profiling import find_header_row, profile_table, read_raw

MAPPERS = {"rules": map_columns}


def evaluate(data_dir: Path, mapper_name: str = "rules") -> dict:
    mapper = MAPPERS[mapper_name]
    stats = defaultdict(lambda: defaultdict(int))
    errors = []

    for truth_path in sorted((data_dir / "truth").glob("*.json")):
        truth = json.loads(truth_path.read_text())
        rows = read_raw(data_dir / "inputs" / truth["file"])
        header_row = find_header_row(rows)
        header_ok = header_row == truth["header_row"]
        predicted = {
            m.source_column: m.target_column
            for m in mapper(profile_table(rows, header_row), truth["dataset_type"])
        }

        groups = ("all", f"split:{truth['split']}", f"type:{truth['dataset_type']}")
        for group in groups:
            stats[group]["files"] += 1
            stats[group]["header_ok"] += header_ok

        for column in truth["columns"]:
            expected = column["target"]
            got = predicted.get(column["header"]) if header_ok else None
            correct = header_ok and got == expected
            for group in groups:
                stats[group]["columns"] += 1
                stats[group]["correct"] += correct
                if expected is not None:
                    stats[group]["target_columns"] += 1
                    stats[group]["target_correct"] += correct
                else:
                    stats[group]["extra_columns"] += 1
                    stats[group]["extra_clean"] += correct
            if not correct:
                errors.append(
                    {
                        "file": truth["file"],
                        "split": truth["split"],
                        "header": column["header"],
                        "expected": expected,
                        "got": got,
                        "header_row_ok": header_ok,
                    }
                )
    return {"stats": {k: dict(v) for k, v in stats.items()}, "errors": errors}


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def render_table(result: dict, mapper_name: str) -> str:
    stats = result["stats"]
    lines = [
        f"## Column mapping accuracy ({mapper_name})",
        "",
        "| Group | Files | Columns | Mapping accuracy | Target-column accuracy | Extra columns left unmapped | Header detected |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    order = ["all", "split:dev", "split:heldout", "type:sales", "type:invoices", "type:stock"]
    for group in order:
        s = stats.get(group)
        if not s:
            continue
        lines.append(
            f"| {group} | {s['files']} | {s['columns']} | {_pct(s['correct'], s['columns'])} "
            f"| {_pct(s.get('target_correct', 0), s.get('target_columns', 0))} "
            f"| {_pct(s.get('extra_clean', 0), s.get('extra_columns', 0))} "
            f"| {_pct(s['header_ok'], s['files'])} |"
        )
    lines += [
        "",
        "Mapping accuracy counts every column, including extra columns that should stay unmapped.",
        "Target-column accuracy counts only columns that belong to the target schema.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", default="benchmark/data", type=Path)
    parser.add_argument("--mapper", default="rules", choices=sorted(MAPPERS))
    parser.add_argument("--show-errors", action="store_true", help="list wrong mappings (dev split only)")
    parser.add_argument("--out", default="benchmark/results/latest.md", type=Path)
    args = parser.parse_args()

    if not (args.data / "truth").exists():
        raise SystemExit(f"No benchmark data in {args.data}. Run `make data` first.")

    result = evaluate(args.data, args.mapper)
    table = render_table(result, args.mapper)
    print(table)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(table + "\n")

    if args.show_errors:
        print("\nMistakes on the dev split:")
        for e in (e for e in result["errors"] if e["split"] == "dev"):
            print(f"  {e['file']}: '{e['header']}' expected={e['expected']} got={e['got']}")


if __name__ == "__main__":
    main()
