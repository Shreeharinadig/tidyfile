"""Read raw CSV/XLSX files, find the header row, and profile each column."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d.%m.%y",
    "%d.%m.%Y",
    "%d/%m/%y",
)

_NUMBER_RE = re.compile(
    r"^\s*(?:rs\.?|inr|₹)?\s*(-?\d[\d,]*(?:\.\d+)?)\s*(?:pcs|nos|units)?\s*$",
    re.IGNORECASE,
)


@dataclass
class ColumnProfile:
    name: str
    index: int
    total: int
    non_empty: int
    inferred_type: str  # date, integer, number, text, empty
    samples: list[str] = field(default_factory=list)


def cell_to_str(value: object) -> str:
    """Turn any spreadsheet cell value into a trimmed string."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.time() == datetime.min.time():
            return value.date().isoformat()
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value).strip()


def read_raw(path: str | Path) -> list[list[str]]:
    """Read the first sheet (or the CSV) as a rectangular grid of strings."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = [[cell_to_str(c) for c in row] for row in csv.reader(handle)]
    elif suffix in (".xlsx", ".xlsm"):
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            sheet = workbook.worksheets[0]
            rows = [[cell_to_str(c) for c in row] for row in sheet.iter_rows(values_only=True)]
        finally:
            workbook.close()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    width = max((len(row) for row in rows), default=0)
    return [row + [""] * (width - len(row)) for row in rows]


def parse_number(text: str) -> float | None:
    match = _NUMBER_RE.match(text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_date(text: str) -> date | None:
    text = text.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def infer_type(values: list[str]) -> str:
    """Classify a column as date, integer, number, text, or empty."""
    present = [v for v in values if v != ""]
    if not present:
        return "empty"
    total = len(present)
    if sum(parse_date(v) is not None for v in present) / total >= 0.8:
        return "date"
    numbers = [parse_number(v) for v in present]
    parsed = [x for x in numbers if x is not None]
    if len(parsed) / total >= 0.8:
        return "integer" if all(x.is_integer() for x in parsed) else "number"
    return "text"


def find_header_row(rows: list[list[str]], max_scan: int = 15) -> int:
    """Return the index of the header row, skipping title and blank rows.

    A header row is the first row that is mostly filled and almost entirely text
    (no numbers or dates). Title rows have too few cells; data rows contain
    numbers or dates.
    """
    scan = rows[:max_scan]
    width = max((sum(1 for c in row if c != "") for row in scan), default=0)
    minimum = max(2, int(0.6 * width))
    for index, row in enumerate(scan):
        cells = [c for c in row if c != ""]
        if len(cells) < minimum:
            continue
        textual = [c for c in cells if parse_number(c) is None and parse_date(c) is None]
        if len(textual) / len(cells) >= 0.9:
            return index
    return 0


def profile_table(rows: list[list[str]], header_row: int) -> list[ColumnProfile]:
    """Profile each named column below the header row."""
    if header_row >= len(rows):
        return []
    header = rows[header_row]
    body = [r for r in rows[header_row + 1 :] if any(c != "" for c in r)]
    profiles: list[ColumnProfile] = []
    for index, name in enumerate(header):
        if name == "":
            continue
        values = [r[index] for r in body]
        non_empty = [v for v in values if v != ""]
        profiles.append(
            ColumnProfile(
                name=name,
                index=index,
                total=len(values),
                non_empty=len(non_empty),
                inferred_type=infer_type(values),
                samples=non_empty[:5],
            )
        )
    return profiles
