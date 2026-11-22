"""Target schemas and the alias dictionary used by the rule-based mapper.

SCHEMAS is shared with the benchmark generator, so the two cannot drift apart.
KNOWN_ALIASES is only the worker's own knowledge: the benchmark generator keeps a
separate, larger pool of header names, so some headers are deliberately unknown to
the rules. That gap is what the LLM mapper has to close.
"""

from __future__ import annotations

# dataset type -> {target column: kind}. Kinds: string, date, integer, number.
SCHEMAS: dict[str, dict[str, str]] = {
    "sales": {
        "order_id": "string",
        "order_date": "date",
        "customer_name": "string",
        "product_name": "string",
        "quantity": "integer",
        "unit_price": "number",
        "total_amount": "number",
        "payment_status": "string",
    },
    "invoices": {
        "invoice_no": "string",
        "invoice_date": "date",
        "due_date": "date",
        "customer_name": "string",
        "amount": "number",
        "tax_amount": "number",
        "status": "string",
    },
    "stock": {
        "sku": "string",
        "product_name": "string",
        "quantity_on_hand": "integer",
        "reorder_level": "integer",
        "unit_cost": "number",
        "warehouse": "string",
    },
}

DATASET_TYPES = tuple(SCHEMAS)

# dataset type -> target column -> header names the rules already know.
KNOWN_ALIASES: dict[str, dict[str, list[str]]] = {
    "sales": {
        "order_id": ["order id", "order no", "order number", "order"],
        "order_date": ["order date", "date", "sale date", "sales date", "bill date"],
        "customer_name": ["customer name", "customer", "client name", "client"],
        "product_name": ["product name", "product", "item name", "item"],
        "quantity": ["quantity", "qty", "units"],
        "unit_price": ["unit price", "price", "rate", "unit rate"],
        "total_amount": ["total amount", "total", "amount", "net amount"],
        "payment_status": ["payment status", "status", "pay status"],
    },
    "invoices": {
        "invoice_no": ["invoice no", "invoice number", "invoice", "bill number"],
        "invoice_date": ["invoice date", "date", "bill date"],
        "due_date": ["due date", "payment due", "due"],
        "customer_name": ["customer name", "customer", "client name", "client", "party name"],
        "amount": ["amount", "invoice amount", "total", "total amount", "bill amount"],
        "tax_amount": ["tax", "tax amount", "gst", "gst amount"],
        "status": ["status", "payment status", "invoice status"],
    },
    "stock": {
        "sku": ["sku", "item code", "product code", "code"],
        "product_name": ["product name", "product", "item name", "item", "description"],
        "quantity_on_hand": ["quantity on hand", "stock", "qty in stock", "closing stock", "on hand"],
        "reorder_level": ["reorder level", "min stock", "reorder quantity", "min level"],
        "unit_cost": ["unit cost", "cost", "cost price", "purchase price"],
        "warehouse": ["warehouse", "location", "godown", "store"],
    },
}
