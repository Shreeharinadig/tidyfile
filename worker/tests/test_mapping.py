from tidyfile_worker.mapping import map_columns, normalize
from tidyfile_worker.profiling import ColumnProfile


def col(name, inferred, index=0):
    return ColumnProfile(name=name, index=index, total=10, non_empty=10, inferred_type=inferred, samples=[])


def targets(mappings):
    return {m.source_column: m.target_column for m in mappings}


def test_normalize_expands_abbreviations_and_strips_punctuation():
    assert normalize("Cust Nm") == "customer name"
    assert normalize("Qty.") == "quantity"
    assert normalize("Tax Amt (INR)") == "tax amount inr"
    assert normalize("Invoice #") == "invoice"


def test_exact_alias_maps_with_high_confidence():
    result = map_columns([col("Customer Name", "text")], "sales")
    assert result[0].target_column == "customer_name"
    assert result[0].confidence >= 0.9


def test_abbreviated_headers_map_through_normalization():
    profiles = [col("Cust Nm", "text", 0), col("Qty.", "integer", 1), col("Inv Date", "date", 2)]
    assert targets(map_columns(profiles[:2], "sales")) == {"Cust Nm": "customer_name", "Qty.": "quantity"}
    assert targets(map_columns([profiles[2]], "invoices")) == {"Inv Date": "invoice_date"}


def test_unknown_headers_stay_unmapped():
    result = map_columns([col("Remarks", "text"), col("Sr No", "integer", 1)], "sales")
    assert all(m.target_column is None for m in result)


def test_type_compatibility_blocks_wrong_mappings():
    # "Date" header over text values must not become a date column.
    assert map_columns([col("Date", "text")], "sales")[0].target_column is None
    # "Amount" header over dates must not become a number column.
    assert map_columns([col("Amount", "date")], "invoices")[0].target_column is None


def test_mapping_is_one_to_one():
    # Both headers look like an amount; only the better one may win the target.
    profiles = [col("Amount", "number", 0), col("Invoice Amount", "number", 1)]
    result = targets(map_columns(profiles, "invoices"))
    assert sorted(v for v in result.values() if v) == ["amount"]
    assert list(result.values()).count(None) == 1


def test_same_header_means_different_targets_per_dataset_type():
    assert map_columns([col("Status", "text")], "sales")[0].target_column == "payment_status"
    assert map_columns([col("Status", "text")], "invoices")[0].target_column == "status"
