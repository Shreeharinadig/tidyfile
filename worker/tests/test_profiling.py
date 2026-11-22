from datetime import date

from tidyfile_worker.profiling import (
    ColumnProfile,
    find_header_row,
    infer_type,
    parse_date,
    parse_number,
    profile_table,
    read_raw,
)


def test_parse_number_handles_indian_formats_and_units():
    assert parse_number("1,23,456.50") == 123456.5
    assert parse_number("₹1,200.00") == 1200.0
    assert parse_number("Rs. 99") == 99.0
    assert parse_number("12 pcs") == 12.0
    assert parse_number("-45.5") == -45.5


def test_parse_number_rejects_text_and_dates():
    assert parse_number("Total") is None
    assert parse_number("12/04/2026") is None
    assert parse_number("SKU-1001") is None
    assert parse_number("") is None


def test_parse_date_handles_mixed_formats():
    assert parse_date("12/04/2026") == date(2026, 4, 12)
    assert parse_date("12-Apr-2026") == date(2026, 4, 12)
    assert parse_date("2026-04-12") == date(2026, 4, 12)
    assert parse_date("12.04.26") == date(2026, 4, 12)
    assert parse_date("not a date") is None


def test_infer_type():
    assert infer_type(["12/04/2026", "13/04/2026", ""]) == "date"
    assert infer_type(["1", "2", "30"]) == "integer"
    assert infer_type(["1.5", "2", "30"]) == "number"
    assert infer_type(["Ravi", "Anita"]) == "text"
    assert infer_type(["", ""]) == "empty"


def test_infer_type_tolerates_a_total_row():
    values = ["10", "20", "30", "40", "50", "Total"]
    assert infer_type(values) == "integer"


def test_find_header_row_skips_title_and_blank_rows():
    rows = [
        ["Kaveri Trading Co", "", ""],
        ["Report generated on 12/04/2026", "", ""],
        ["", "", ""],
        ["Date", "Customer", "Amount"],
        ["12/04/2026", "Ganesh Medicals", "1,200.00"],
        ["13/04/2026", "Annapurna Stores", "900.00"],
    ]
    assert find_header_row(rows) == 3


def test_find_header_row_when_header_is_first():
    rows = [["Item", "Qty", "Rate"], ["Pen", "10", "5.50"], ["Book", "3", "80"]]
    assert find_header_row(rows) == 0


def test_profile_table_ignores_blank_rows_and_unnamed_columns():
    rows = [
        ["Name", "Qty", ""],
        ["Pen", "10", ""],
        ["", "", ""],
        ["Book", "3", ""],
    ]
    profiles = profile_table(rows, 0)
    assert [p.name for p in profiles] == ["Name", "Qty"]
    assert profiles[1] == ColumnProfile(
        name="Qty", index=1, total=2, non_empty=2, inferred_type="integer", samples=["10", "3"]
    )


def test_read_raw_csv_keeps_blank_rows_and_pads_width(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("Title\n\nA,B,C\n1,2,3\n", encoding="utf-8")
    rows = read_raw(path)
    assert rows[0] == ["Title", "", ""]
    assert rows[1] == ["", "", ""]
    assert rows[2] == ["A", "B", "C"]
    assert find_header_row(rows) == 2
