# Brief C: H1 2026 invoice-to-capture reconciliation

**Audience:** COO and Finance controller
**Period:** 1 January–30 June 2026, India time
**Observation cutoff:** 15 July 2026, India time

This follows the H1 volume check: active booked test lines grew 3.49% against 18.26% implied by plan. The finance bridge below is also H1-based. Monetary figures in this brief are in **crores of rupees**; the audit CSVs retain exact rupee amounts.

## Board sentence

> At H1 2026 close, positive invoice balances totaled **₹1.648 crore** across **9,824 of 162,876 invoices** (**₹26.828 crore billed**): 9,808 had no captured match and 16 were partial; through 15 July, none of those no-match H1 invoices had a later captured payment, leaving **₹1.648 crore** in positive balances, while 1,564 H1 captured attempts worth **₹0.271 crore** had no safe invoice match—Finance should pursue the open invoice list and resolve unmatched captures before calling the difference lost.

Positive balances are calculated invoice by invoice; overcaptures on other invoices are kept separate and are not used to offset unrelated balances.

## H1 invoice bridge

| H1 2026 item | Rows / invoices | Amount (₹ crore) | Rule |
|---|---:|---:|---|
| Invoices dated 1 Jan–30 Jun | 162,876 invoices | 26.828 | One row per unique invoice ID |
| Captured attempts safely matched by 30 Jun | 153,764 attempts across 153,068 invoices | 25.299 | Captured status; matched attempts summed by invoice |
| Invoices with no matched capture by 30 Jun | 9,808 invoices | 1.647 face value | No captured attempt matched by the H1 cutoff |
| Partially paid invoices by 30 Jun | 16 invoices | 0.002 remaining | Invoice balance after matched captures |
| Positive invoice balances by 30 Jun | 9,824 invoices | 1.648 | Sum of positive invoice balances; no cross-invoice offsets |
| Overcaptured invoices by 30 Jun | 712 invoices | 0.119 above invoice amount | Reported separately |
| Later captures against H1 invoices with no H1 capture | 0 invoices | 0.000 | Observed through 15 Jul 2026 |
| Positive invoice balances still open by 15 Jul | 9,824 invoices | 1.648 | Balance through the observation cutoff |

## H1 payment attempts

| H1 2026 payment activity | Attempts | Amount (₹ crore) | Treatment |
|---|---:|---:|---|
| Captured attempts | 158,252 | 26.017 | Gateway status `captured` |
| Captured attempts with a safe invoice match | 156,688 | 25.746 | Invoice reference rule below |
| Captured attempts without a safe invoice match | 1,564 | 0.271 | Kept as an exception list for Finance |
| Failed attempts | 6,234 | 1.017 | Not counted as receipts |

The invoice-cohort match total and the H1 payment-attempt total differ because the first measures captures attached to invoices issued in H1 by the cutoff, while the second measures attempts created during H1. They are separate views of the bridge and should not be added together.

## All-source context

The full supplied files cover invoices dated 30 Dec 2024–30 Jun 2026 and gateway attempts through 15 Jul 2026. Across those full source windows there are **470,776 invoices totaling ₹73.70 crore** and **455,469 captured attempts totaling ₹71.25 crore gross**. Safe invoice matching covers **₹70.52 crore**; **4,588 captured attempts totaling ₹0.73 crore** remain unmatched. These totals are not the H1 bridge and do not form a same-period collection rate.

## Matching and settlement checks

The matching rule is exact `invoice_id` first; otherwise remove hyphens from the trimmed, uppercased reference and match only when the invoice key is unique. No canonical collisions were found. Amount/date similarity is not used to guess identity. Across all source periods, 468,742 of 473,507 gateway rows map to an invoice; 4,765 do not.

The 196 settlement rows dated in H1 show gross **₹25.496 crore**, fees **₹0.522 crore**, tax **₹0.094 crore**, and calculated net **₹24.880 crore**. Captures linked to those settlement IDs total **₹26.112 crore** across supplied payment dates, **₹0.616 crore** above settlement gross. This is a diagnostic, not a bank reconciliation: payment and settlement date windows differ, and the source pack has no independent bank statement or validated clinic cash register.

## Audit and rebuild

The analysis script is [`analyze_brief_c_reconciliation.py`](../analyze_brief_c_reconciliation.py). It reads the cleaned rupee amounts as exact decimals and applies H1 boundaries in `Asia/Kolkata`.

```powershell
python analyze_brief_c_reconciliation.py --data-dir data/clean/brief_c --output-dir outputs/brief_c --year 2026 --observation-cutoff 2026-07-15
```

[`finance_bridge_summary.csv`](../outputs/brief_c/finance_bridge_summary.csv) and [`finance_all_period_summary.csv`](../outputs/brief_c/finance_all_period_summary.csv) show crores alongside exact rupee amounts for audit. The JSON summary retains exact rupee values, dates, counts, matching coverage and limitations. Row-level Finance action lists are written under the ignored `data/clean/brief_c/actions/` folder and are not committed.

The bridge remains provisional until Finance confirms source completeness, refunds/reversals, cash coverage, and the settlement-to-bank match. A missing captured gateway match does not prove permanent nonpayment.
