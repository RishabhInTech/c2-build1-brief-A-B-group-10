# Brief C: verify the cleaned CSVs

These checks inspect the cleaned files only. They do not repair values, remove rows, or decide which payment attempts count as collected money. Run them after generating the local `data/clean/brief_c/` files:

```python
from pathlib import Path
import pandas as pd

folder = Path("data/clean/brief_c")
payments = pd.read_csv(folder / "gateway_payments.csv")
invoices = pd.read_csv(folder / "invoices.csv")

print("Payments:", payments.shape)
print(payments.dtypes)
print("Invoices:", invoices.shape)
print(invoices.dtypes)

print("Payment missing values:\n", payments.isna().sum())
print("Invoice missing values:\n", invoices.isna().sum())
print("Exact duplicate payment rows:", payments.duplicated().sum())
print("Exact duplicate invoice rows:", invoices.duplicated().sum())
print("Duplicate payment IDs:", payments["payment_id"].duplicated().sum())
print("Duplicate invoice IDs:", invoices["invoice_id"].duplicated().sum())

payment_refs = set(payments["invoice_ref"].dropna().astype(str))
invoice_ids = set(invoices["invoice_id"].dropna().astype(str))
print("Unique payment references without exact invoice ID match:",
      len(payment_refs - invoice_ids))
```

## Results from the current cleaned files

| Check | Result |
|---|---:|
| Gateway payment rows | 473,507 |
| Invoice rows | 470,776 |
| Exact duplicate payment rows | 0 |
| Exact duplicate invoice rows | 0 |
| Duplicate payment IDs | 0 |
| Duplicate invoice IDs | 0 |
| Rows with blank settlement ID | 18,038 |
| Unique normalized payment references | 453,956 |
| Unique references with no exact invoice ID match | 94,172 |
| Unique references with an exact invoice ID match | 359,784 |

The blank settlement IDs occur on payment attempts that have no settlement ID recorded; they should be interpreted by payment status and source rules. The exact-reference comparison is only a baseline. The known reference variants (such as missing hyphens or unexpected suffix lengths) explain why many references do not match literally; do not label these as unpaid invoices or unmatched payments until a documented mapping rule is evaluated.

Duplicate rows, duplicate IDs, and multiple payment attempts are different checks. A repeated invoice reference can be a legitimate retry or another attempt and is not proof that a gateway row is duplicated. Preserve attempts until the analysis distinguishes statuses and establishes which amount is collected.
