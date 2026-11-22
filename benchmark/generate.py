"""Synthetic benchmark generator for tidyfile.

Produces messy business files (CSV and XLSX) together with ground truth, so the
mapping and cleaning stages can be measured. Everything is seeded: the same seed
always produces the same logical content.

Output layout (under --out):
    inputs/    the messy files a user would upload
    truth/     one JSON per file: header row, column mapping, mess applied
    expected/  one CSV per file: the correct cleaned dataset
    manifest.json

Usage:
    PYTHONPATH=worker:benchmark python3 benchmark/generate.py --out benchmark/data --seed 42
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook

from tidyfile_worker.schemas import SCHEMAS

DEFAULT_SEED = 42
FILES_PER_TYPE = {"sales": 18, "invoices": 17, "stock": 15}
HELDOUT_REMAINDERS = (0, 3, 6)  # file index % 10; gives 15 held-out files of 50
DATE_FORMATS = ["%d/%m/%Y", "%d-%b-%Y", "%Y-%m-%d", "%d.%m.%y", "%d-%m-%Y"]

OPTIONAL_COLUMNS = {
    "sales": ["payment_status"],
    "invoices": ["tax_amount", "due_date"],
    "stock": ["warehouse", "reorder_level"],
}

# target column -> (common headers, obscure headers). Obscure ones are mostly
# unknown to the rule-based mapper.
ALIASES: dict[str, tuple[list[str], list[str]]] = {
    "order_id": (["Order ID", "Order No", "Order Number", "Ord No"], ["Ref", "Memo #", "Doc No", "Slip"]),
    "order_date": (["Order Date", "Date", "Sale Date"], ["Dt", "Txn Dt", "Booked On", "Dated"]),
    "customer_name": (
        ["Customer Name", "Customer", "Client Name", "Cust Name"],
        ["Cust Nm", "Party", "Buyer", "Particulars", "Sold To"],
    ),
    "product_name": (["Product Name", "Product", "Item Name", "Item"], ["Goods", "Prod", "Material", "Article"]),
    "quantity": (["Quantity", "Qty", "Qty."], ["Nos", "Units Sold", "Pcs", "No of Units"]),
    "unit_price": (["Unit Price", "Price", "Rate"], ["Rate/Unit", "MRP", "Per Unit", "Selling Price"]),
    "total_amount": (["Total Amount", "Total", "Amount"], ["Net Amt", "Value", "Line Total", "Sale Value"]),
    "payment_status": (["Payment Status", "Status"], ["Pmt", "Paid?", "Settlement", "Pay Stat"]),
    "invoice_no": (["Invoice No", "Invoice Number", "Invoice #", "Inv No"], ["Voucher No", "Doc Ref", "Inv Ref", "Serial"]),
    "invoice_date": (["Invoice Date", "Date", "Inv Date"], ["Billed On", "Dt", "Voucher Dt", "Raised On"]),
    "due_date": (["Due Date", "Payment Due"], ["Pay By", "Due On", "Maturity", "Settle By"]),
    "amount": (["Amount", "Invoice Amount", "Total"], ["Bill Value", "Gross", "Amt Payable", "Net Payable"]),
    "tax_amount": (["Tax", "Tax Amount", "GST"], ["GST Amt", "Levy", "Tax Amt (INR)", "IGST+CGST"]),
    "status": (["Status", "Payment Status"], ["State", "Paid/Unpaid", "Collected?", "Stage"]),
    "sku": (["SKU", "Item Code", "Product Code"], ["Part No", "Stock Code", "Art No", "Catalog Ref"]),
    "quantity_on_hand": (
        ["Quantity on Hand", "Stock", "Qty in Stock", "Closing Stock"],
        ["On Hand", "Bal Qty", "Available", "Stk"],
    ),
    "reorder_level": (["Reorder Level", "Min Stock", "Reorder Qty"], ["Safety Stock", "Min Lvl", "Trigger Qty", "ROL"]),
    "unit_cost": (["Unit Cost", "Cost", "Cost Price"], ["Purchase Rate", "Landed Cost", "CP", "Buy Price"]),
    "warehouse": (["Warehouse", "Location", "Godown"], ["Bin", "Site", "Depot", "Shed"]),
}

CUSTOMERS = [
    "Sri Lakshmi Traders", "Ganesh Medicals", "Kaveri Hardware", "Annapurna Stores", "Mysore Agro Supplies",
    "Basava Electricals", "Chamundi Enterprises", "Durga Textiles", "Eshwar Paints", "Fresh Basket Mart",
    "Gowda Brothers", "Hoysala Foods", "Indira Stationers", "Jayanagar Pharma", "Karnataka Steel Works",
    "Lakshmi Narayan Sons", "Malnad Coffee Co", "Nandi Dairy Depot", "Om Sai Distributors", "Panchajanya Books",
    "Quality Tools Centre", "Rajeshwari Silks", "Sapthagiri Cements", "Tungabhadra Rice Mill", "Udupi Spices",
    "Vijaya Auto Parts", "Western Ghats Tea", "Yelahanka Plywood", "Zenith Packaging", "Anand Sweets",
    "Bharath Cycles", "Cauvery Plumbing", "Deccan Glassworks", "Ekta Garments", "Friends Tyres",
    "Gayathri Jewellers", "Hubli Oil Mills", "Iyer Bakery", "Jagadamba Cloth House", "Kamat Frames",
]

PRODUCTS = [
    ("Steel Water Bottle 1L", 349), ("Notebook A4 200pg", 85), ("LED Bulb 9W", 120), ("Cotton Towel", 260),
    ("Basmati Rice 5kg", 540), ("Sunflower Oil 1L", 165), ("Paracetamol Strip", 32), ("Hand Sanitizer 500ml", 140),
    ("PVC Pipe 1in", 210), ("Wall Paint 4L", 1380), ("Ceiling Fan", 2150), ("Extension Board", 430),
    ("Ballpoint Pen Box", 95), ("Tea Powder 1kg", 410), ("Detergent 2kg", 310), ("Plastic Chair", 690),
    ("Steel Plate Set", 780), ("Door Lock", 560), ("Cement Bag 50kg", 395), ("Copper Wire 90m", 1650),
    ("Face Mask Pack", 150), ("Bath Soap 4pk", 180), ("Mixer Grinder", 3200), ("Spice Mix 200g", 110),
    ("School Bag", 880), ("Torch Light", 240), ("Water Filter Cartridge", 920), ("Tyre Tube", 310),
    ("Coffee Powder 500g", 360), ("Plywood Sheet 8x4", 1890),
]

COMPANIES = [
    "Sri Ganesh Distributors", "Kaveri Trading Co", "Bangalore Supply House", "Mysore Wholesale Mart",
    "Hubli General Traders", "Coastal Agencies", "Deccan Enterprises", "Malnad Merchants",
]
WAREHOUSES = ["Bengaluru Main", "Hubli", "Mysuru", "Mangaluru"]
PEOPLE = ["Ravi", "Anita", "Suresh", "Meena", "Kiran", "Divya"]
REMARKS = ["", "", "", "", "urgent", "call back", "check stock", "gift pack", "bulk deal"]


# --------------------------------------------------------------------------- #
# Canonical (clean) data
# --------------------------------------------------------------------------- #
def _rand_date(rng: random.Random) -> date:
    return date(2025, 4, 1) + timedelta(days=rng.randrange(0, 365))


def gen_sales(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for k in range(n):
        product, base = rng.choice(PRODUCTS)
        quantity = rng.randint(1, 50)
        price = round(base * rng.uniform(0.9, 1.1), 2)
        rows.append(
            {
                "order_id": f"ORD-{10000 + k}",
                "order_date": _rand_date(rng),
                "customer_name": rng.choice(CUSTOMERS),
                "product_name": product,
                "quantity": quantity,
                "unit_price": price,
                "total_amount": round(quantity * price, 2),
                "payment_status": rng.choice(["Paid", "Pending", "Partial"]),
            }
        )
    return rows


def gen_invoices(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for k in range(n):
        issued = _rand_date(rng)
        amount = round(rng.uniform(2000, 250000), 2)
        rows.append(
            {
                "invoice_no": f"INV/2025-26/{k + 1:04d}",
                "invoice_date": issued,
                "due_date": issued + timedelta(days=rng.choice([15, 30, 45])),
                "customer_name": rng.choice(CUSTOMERS),
                "amount": amount,
                "tax_amount": round(amount * 0.18, 2),
                "status": rng.choice(["Paid", "Open", "Overdue"]),
            }
        )
    return rows


def gen_stock(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for k in range(n):
        product, base = rng.choice(PRODUCTS)
        rows.append(
            {
                "sku": f"SKU-{1000 + k}",
                "product_name": product,
                "quantity_on_hand": rng.randint(0, 500),
                "reorder_level": rng.randint(10, 100),
                "unit_cost": round(base * rng.uniform(0.55, 0.8), 2),
                "warehouse": rng.choice(WAREHOUSES),
            }
        )
    return rows


GENERATORS = {"sales": gen_sales, "invoices": gen_invoices, "stock": gen_stock}
SUM_COLUMNS = ("total_amount", "amount", "quantity_on_hand")


# --------------------------------------------------------------------------- #
# Messy rendering
# --------------------------------------------------------------------------- #
def indian_group(value: float, decimals: int = 2) -> str:
    """Format with Indian digit grouping, e.g. 1,23,456.50."""
    text = f"{abs(value):.{decimals}f}"
    whole, _, frac = text.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    result = whole + ("." + frac if frac else "")
    return "-" + result if value < 0 else result


def _typo(rng: random.Random, text: str) -> str:
    if len(text) < 6:
        return text
    i = rng.randrange(1, len(text) - 2)
    if rng.random() < 0.5:
        return text[:i] + text[i + 1 :]  # drop a character
    return text[:i] + text[i + 1] + text[i] + text[i + 2 :]  # swap neighbours


def _pick_headers(rng: random.Random, targets: list[str]) -> tuple[dict[str, str], int]:
    used: set[str] = set()
    chosen: dict[str, str] = {}
    obscure = 0
    for target in targets:
        common, rare = ALIASES[target]
        pool = rare if rng.random() < 0.3 else common
        options = [a for a in pool if a.lower() not in used]
        if not options:
            options = [a for a in common + rare if a.lower() not in used]
        alias = rng.choice(options)
        used.add(alias.lower())
        chosen[target] = alias
        obscure += alias in rare
    return chosen, obscure


def _money(value: float, style: str, native: bool) -> object:
    if style == "plain":
        return float(value) if native else f"{value:.2f}"
    grouped = indian_group(value)
    if style == "comma":
        return grouped
    if style == "rupee":
        return "₹" + grouped
    return "Rs. " + grouped  # "rs"


def _render(rng, kind, target, value, style, native):
    if kind == "date":
        return value if style["native_dates"] else value.strftime(rng.choice(style["date_formats"]))
    if kind == "number":
        return _money(value, style["amount"].get(target, "plain"), native)
    if kind == "integer":
        if target == "quantity" and style["qty_unit"]:
            return f"{value} pcs"
        return value if native else str(value)
    # strings
    if target == "customer_name":
        text = value
        roll = rng.random()
        if style["typos"] and roll < 0.08:
            text = _typo(rng, text)
        elif style["case_noise"] and roll < 0.2:
            text = text.upper() if rng.random() < 0.5 else text.lower()
        if style["whitespace"] and rng.random() < 0.1:
            text = f"  {text} " if rng.random() < 0.5 else f"{text}  "
        return text
    if target in ("payment_status", "status"):
        return rng.choice([value, value.upper(), value.lower()])
    return value


def _write_csv(path: Path, rows: list[list]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow(["" if cell is None else cell for cell in row])


def _write_xlsx(path: Path, rows: list[list]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    workbook.properties.creator = "tidyfile-benchmark"
    workbook.properties.created = datetime(2026, 1, 1)
    workbook.properties.modified = datetime(2026, 1, 1)
    for row in rows:
        sheet.append(row if row else [None])
    workbook.save(path)


def _expected_cell(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def build_file(seed: int, index: int, dtype: str, out: Path) -> dict:
    rng = random.Random(f"{seed}-{index}")
    is_xlsx = rng.random() < 0.6
    ext = "xlsx" if is_xlsx else "csv"
    n_rows = rng.randint(30, 120)
    canonical = GENERATORS[dtype](rng, n_rows)

    schema = SCHEMAS[dtype]
    dropped = [t for t in OPTIONAL_COLUMNS[dtype] if rng.random() < 0.15]
    present = [t for t in schema if t not in dropped]
    headers, obscure = _pick_headers(rng, present)

    style = {
        "date_formats": rng.sample(DATE_FORMATS, rng.choice([1, 2])),
        "native_dates": is_xlsx and rng.random() < 0.25,
        "amount": {t: rng.choice(["plain", "comma", "rupee", "rs"]) for t in present if schema[t] == "number"},
        "qty_unit": rng.random() < 0.1,
        "typos": rng.random() < 0.4,
        "case_noise": rng.random() < 0.4,
        "whitespace": rng.random() < 0.4,
    }

    columns = [(headers[t], t, schema[t]) for t in present]
    extras = rng.sample(["Sr No", "Remarks", "Salesperson", "Contact"], rng.choice([0, 1, 2]))
    columns += [(name, None, "string") for name in extras]
    rng.shuffle(columns)

    body = []
    for k, record in enumerate(canonical):
        row = []
        for header, target, kind in columns:
            if target is not None:
                row.append(_render(rng, kind, target, record[target], style, is_xlsx))
            elif header == "Sr No":
                row.append(str(k + 1))
            elif header == "Remarks":
                row.append(rng.choice(REMARKS))
            elif header == "Salesperson":
                row.append(rng.choice(PEOPLE))
            else:
                row.append(f"9{rng.randint(100000000, 999999999)}")
        body.append(row)

    duplicates = int(len(body) * rng.uniform(0, 0.05))
    for _ in range(duplicates):
        source = rng.randrange(len(body))
        body.insert(rng.randint(source + 1, len(body)), list(body[source]))

    has_total = rng.random() < 0.3
    sum_col = next((i for i, (_, t, _) in enumerate(columns) if t in SUM_COLUMNS), None)
    if has_total and sum_col is not None:
        target = columns[sum_col][1]
        total_value = sum(r[target] for r in canonical)
        total_row = [""] * len(columns)
        total_row[sum_col] = (
            _money(total_value, style["amount"].get(target, "plain"), is_xlsx)
            if schema[target] == "number"
            else (total_value if is_xlsx else str(total_value))
        )
        total_row[0 if sum_col != 0 else 1] = "Total"
        body.append(total_row)
    else:
        has_total = False

    title_count = rng.choice([0, 0, 1, 2, 3])
    title_rows: list[list] = []
    if title_count >= 1:
        title_rows.append([rng.choice(COMPANIES)])
    if title_count >= 2:
        stamp = _rand_date(rng).strftime(rng.choice(DATE_FORMATS))
        title_rows.append([f"Report generated on {stamp}"])
    if title_count >= 3:
        title_rows.append([])

    all_rows = title_rows + [[name for name, _, _ in columns]] + body
    name = f"{index + 1:02d}_{dtype}.{ext}"
    (out / "inputs").mkdir(parents=True, exist_ok=True)
    (_write_xlsx if is_xlsx else _write_csv)(out / "inputs" / name, all_rows)

    (out / "expected").mkdir(parents=True, exist_ok=True)
    with (out / "expected" / f"{Path(name).stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(present)
        for record in canonical:
            writer.writerow([_expected_cell(record[t]) for t in present])

    messes = []
    if title_count:
        messes.append(f"title_rows={title_count}")
    if len(style["date_formats"]) > 1:
        messes.append("mixed_date_formats")
    if style["native_dates"]:
        messes.append("native_dates")
    if any(s != "plain" for s in style["amount"].values()):
        messes.append("formatted_amounts")
    if style["qty_unit"]:
        messes.append("quantity_units")
    if style["typos"]:
        messes.append("name_typos")
    if style["case_noise"]:
        messes.append("name_case")
    if style["whitespace"]:
        messes.append("name_whitespace")
    if duplicates:
        messes.append(f"duplicates={duplicates}")
    if has_total:
        messes.append("total_row")
    if extras:
        messes.append(f"extra_columns={len(extras)}")
    if obscure:
        messes.append(f"obscure_headers={obscure}")
    if dropped:
        messes.append("dropped=" + "+".join(dropped))

    truth = {
        "file": name,
        "dataset_type": dtype,
        "split": "heldout" if index % 10 in HELDOUT_REMAINDERS else "dev",
        "header_row": len(title_rows),
        "columns": [{"header": h, "target": t} for h, t, _ in columns],
        "expected_rows": len(canonical),
        "messes": messes,
    }
    (out / "truth").mkdir(parents=True, exist_ok=True)
    (out / "truth" / f"{Path(name).stem}.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False))
    return truth


def generate(out: Path, seed: int = DEFAULT_SEED) -> list[dict]:
    """Generate the whole benchmark into `out`, replacing any previous output."""
    out = Path(out)
    for sub in ("inputs", "truth", "expected"):
        shutil.rmtree(out / sub, ignore_errors=True)
    types = [t for t, count in FILES_PER_TYPE.items() for _ in range(count)]
    random.Random(seed).shuffle(types)

    entries = [build_file(seed, i, dtype, out) for i, dtype in enumerate(types)]

    digest = hashlib.sha256()
    for entry in entries:
        stem = Path(entry["file"]).stem
        digest.update((out / "truth" / f"{stem}.json").read_bytes())
        digest.update((out / "expected" / f"{stem}.csv").read_bytes())
    manifest = {
        "seed": seed,
        "files": [{k: e[k] for k in ("file", "dataset_type", "split")} for e in entries],
        "fingerprint": digest.hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="benchmark/data", type=Path)
    parser.add_argument("--seed", default=DEFAULT_SEED, type=int)
    args = parser.parse_args()
    entries = generate(args.out, args.seed)
    heldout = sum(e["split"] == "heldout" for e in entries)
    print(f"Generated {len(entries)} files ({heldout} held out) in {args.out} with seed {args.seed}")


if __name__ == "__main__":
    main()
