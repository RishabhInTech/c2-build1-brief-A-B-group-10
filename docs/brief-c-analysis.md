# Brief C: Q2 2026 invoice-to-capture reconciliation

**Audience:** Dr Priya Menon, COO; Finance controller

**Analysis status:** Reproduced from the full local finance pack on 2026-10-24

**Quarter choice:** Q2 2026, following the H1 2026 project context; the sponsor should confirm because the source prompt does not name a year.

This is the second analysis step. The project first checked H1 active booked test volume against plan; after excluding 3,541 superseded reschedule lines, growth was 3.49% against 18.26% implied plan growth. See [`project-analysis.md`](project-analysis.md) for the calculation and city/month/channel diagnosis.

## Board sentence

> At Q2 2026 close, ₹14.105m remained as positive invoice balances on 8,356 of 79,246 invoices (₹132.847m billed): 8,344 had no captured match and 12 were partial; by 15 July, 1,763 of the no-match invoices had later matched captures against ₹2.982m of invoice value, leaving ₹11.123m still outstanding, while 747 Q2 captures worth ₹1.323m had no invoice match—Finance should pursue the residual invoice list and resolve the unmatched captures before calling the difference lost.

The board number is invoice-wise positive balance, not a net across invoices. Captured overpayments on other invoices are reported separately and must not be used to offset unrelated balances without Finance approval.

## Full supplied-period totals

The roughly ₹72–73 crore figure is correct for **all supplied invoice periods**, not Q2 alone. The source pack contains **470,776 invoices totaling ₹737,020,069 (₹73.70 crore)**, dated 30 Dec 2024 through 30 Jun 2026. The gateway pack contains **455,469 captured attempts totaling ₹712,489,133 (₹71.25 crore gross)**, dated through 15 Jul 2026. Of the captured amount, **₹705,219,725 (₹70.52 crore)** has a safe invoice match; **4,588 captured attempts totaling ₹7,269,408 (₹0.73 crore)** do not.

These are source-wide totals across different date windows, not a same-period collection rate or a bank reconciliation. “Captured” means the gateway status is `captured`; it does not by itself establish invoice allocation or bank settlement. The Q2-only board bridge above remains **₹132.847m billed (₹13.28 crore)**, with **₹119.266m (₹11.93 crore)** in safely matched captures by quarter end. The all-period audit rows are in [`finance_all_period_summary.csv`](../outputs/brief_c/finance_all_period_summary.csv), with rupee-precision values.

## Headline bridge

| Q2 2026 item | Rows / invoices | INR | Rule |
|---|---:|---:|---|
| Invoices dated 1 Apr–30 Jun | 79,246 invoices | ₹132,847,274.00 | Invoice date in India quarter; one row per unique invoice ID |
| Captured payments matched by 30 Jun 23:59 IST | 71,211 payment attempts across 70,902 invoices | ₹119,265,677.00 | Captured status only; all matched attempts summed per invoice |
| Invoices with no matched capture at quarter close | 8,344 invoices | ₹14,090,027.00 face value | No captured attempt matched to the invoice by cutoff |
| Partially paid at quarter close | 12 invoices | ₹14,836.00 remaining balance | Face value ₹22,945; subtract matched capture amount |
| Positive invoice balances at quarter close | 8,356 invoices | ₹14,104,863.00 | Sum invoice-level positive balances; no cross-invoice offsets |
| Overcaptured at quarter close | 318 invoices | ₹523,266.00 above invoice amount | Kept separate from positive balances |
| Later captures against quarter-close no-capture invoices | 1,763 invoices | ₹2,982,123.00 invoice face value | Captures observed through 15 Jul 2026 IST; latest supplied gateway date is 15 Jul IST |
| Positive invoice balances still open by 15 Jul | 6,594 invoices | ₹11,123,190.00 | Invoice-level remaining balance through observation cutoff |
| Q2 captured attempts with no invoice match | 747 payment attempts | ₹1,323,051.00 | Payment timestamp in Q2; captured status; no safe reference match |
| Q2 failed attempts | 2,954 payment attempts | ₹4,911,580.00 | Excluded from collections |

The bridge's row and amount controls are in [`outputs/brief_c/finance_bridge_summary.csv`](../outputs/brief_c/finance_bridge_summary.csv); all dimensions and rules are in [`outputs/brief_c/finance_bridge_summary.json`](../outputs/brief_c/finance_bridge_summary.json). The JSON retains the matched-reference totals, settlement diagnostic, and limitations.

## Reference rule and coverage

The rule is exact `invoice_id` match first; otherwise remove only hyphens from the already trimmed, uppercased payment reference and require a unique canonical invoice key. There are no canonical collisions. This maps 93,132 separator-free reference rows to an invoice. References with a seven-digit suffix remain unmatched; amount/date similarity is not used as identity evidence. Across the full gateway file, 468,742 of 473,507 payment attempts map to an invoice; 4,765 do not. Among captured attempts across all supplied dates, 4,588 rows totaling ₹7,269,408 remain unmatched.

For Q2 payment timestamps, 75,115 attempts were captured for ₹125,656,682; 74,368 rows totaling ₹124,333,631 had a safe invoice match, and 747 totaling ₹1,323,051 did not. The failed-attempt amount is shown for context only and is not collected cash. Payment attempts were not deduplicated: multiple genuine captures on one invoice can create partial balances or overcaptures, so Finance should review those invoice-level rows.

## Settlement check

The 91 settlement rows dated in Q2 show gross ₹123,266,859.98, fees ₹2,524,925.44, tax ₹454,486.58, and calculated net ₹120,287,447.96. Captured attempts linked to those settlement IDs sum to ₹126,246,272.00, ₹2,979,412.02 above settlement gross. This is not reconciled: payment and settlement date windows differ, and the supplied files do not include an independent bank statement or a validated clinic cash register. Do not describe the calculated net as bank cash received until Finance reconciles the settlement IDs and date cutoffs.

## Audit and rebuild

The analysis script is [`analyze_brief_c_reconciliation.py`](../analyze_brief_c_reconciliation.py). It uses integer paise for addition, compares quarter boundaries in `Asia/Kolkata`, retains the source-reference fields, and writes aggregate output separately from private row-level action lists.

```powershell
python analyze_brief_c_reconciliation.py --data-dir data/clean/brief_c --output-dir outputs/brief_c --year 2026 --quarter 2 --observation-cutoff 2026-07-15
```

The action lists are written under ignored `data/clean/brief_c/actions/` and retain invoice/payment IDs, source files and source rows for Finance. Do not commit those files. They contain the Q2 positive invoice balances and the Q2 unmatched captured attempts.

The Q2 2026 conclusion is provisional until the COO/Finance controller confirms the quarter year, the quarter-end cutoff, and source coverage for cash, reversals/refunds and bank settlement. A missing matched gateway row means no match in these supplied gateway data, not proof that the invoice is permanently unpaid.
