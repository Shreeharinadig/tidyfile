## Column mapping accuracy (rules)

| Group | Files | Columns | Mapping accuracy | Target-column accuracy | Extra columns left unmapped | Header detected |
| --- | --- | --- | --- | --- | --- | --- |
| all | 50 | 399 | 77.9% | 74.5% | 100.0% | 100.0% |
| split:dev | 35 | 280 | 77.1% | 73.4% | 100.0% | 100.0% |
| split:heldout | 15 | 119 | 79.8% | 76.9% | 100.0% | 100.0% |
| type:sales | 18 | 157 | 80.3% | 78.0% | 100.0% | 100.0% |
| type:invoices | 17 | 138 | 73.9% | 69.0% | 100.0% | 100.0% |
| type:stock | 15 | 104 | 79.8% | 76.1% | 100.0% | 100.0% |

Mapping accuracy counts every column, including extra columns that should stay unmapped.
Target-column accuracy counts only columns that belong to the target schema.
