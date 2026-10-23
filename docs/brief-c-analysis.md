# Brief C: Money — current analysis status

**Selected as the final board-facing brief:** 2026-10-24  
**Status:** finance sources cleaned and profiled; invoice-reference mapping, matching and bridge analysis remain to be done.  
**Audience:** Dr Priya Menon, COO; Finance controller.

## Project story

The work began with Brief A's question about H1 volume growth and Brief B's booking-system transition in Chennai and Jaipur. Those checks provided useful context but did not establish a cause for the growth gap. Brief D then checked whether a clinic's no-show rate was a strong explanation; after accounting for appointment mix and the scan across clinics, it produced no reliable clinic-level outlier. The team therefore selected Brief C as the final focus: a finance bridge that can explain which parts of billed revenue became captured payments, which records do not match, and which differences come from timing.

The Brief D conclusion is a no-finding on clinic performance, not proof that no clinic problem exists. Its CHE-03 capture gap remains separate follow-up work. Brief C now owns the main question and the final COO recommendation.

## The COO's question

> “Which invoices were never paid, which payments match no invoice, and how much of the gap is only timing?”

The requested deliverable is a bridge from invoiced to collected. Every bar must include a count and an amount, both sides must reconcile, and Finance must receive a list it can act on. The bridge should distinguish failed payment attempts, captured payments, unmatched references, payments received after the invoice quarter, and settlement gross versus fees/tax/net.

## Cleaning completed

The finance-only cleaning run used invoice, gateway-payment, and settlement sources. It retained all source rows, left `cleaned/` untouched, omitted patient names and patient IDs, kept booking ID to validate the one-invoice-per-visit expectation, normalized invoice references while retaining their raw form, converted paise to exact INR, and added UTC/India timestamps from the source epochs.

| Dataset | Source rows retained | Duplicate primary-key rows | Rejected |
|---|---:|---:|---:|
| Invoices | 470,776 | 0 | 0 |
| Gateway payment attempts | 473,507 | 0 | 0 |
| Settlements | 562 | 0 | 0 |

The gateway export contains 455,469 captured and 18,038 failed attempts. It includes UPI, card, cash, and netbanking method labels. The overall file includes invoice dates from 2024-12-30 through 2026-06-30, payments through 2026-07-14 UTC, and settlements through 2026-07-15 UTC, so adjacent periods are available for timing analysis.

The main data-quality issue is **95,921 gateway invoice references with non-dominant formats**. The common variant omits hyphens; some references also have a different suffix length. Their raw and normalized values are retained. No numeric-only or fuzzy match has been applied. The team needs to compare candidate rules, record collision counts and unmatched rows, and agree the mapping with Finance before claiming that any invoice was never paid.

The handbook says “second quarter” without a year. Q2 2025 and Q2 2026 both appear in the files. The quarter year and collection cutoff remain open and must be confirmed before constructing the headline bridge. All supplied periods were retained at cleaning time to avoid dropping late payments or settlements.

## Analysis plan

1. Profile ID formats, dates, amounts, duplicate keys, payment status/method and source coverage. Aggregated profile: [`outputs/brief_c/finance_profile.json`](../outputs/brief_c/finance_profile.json); reference issue counts: [`outputs/brief_c/quality_issue_summary.csv`](../outputs/brief_c/quality_issue_summary.csv).
2. Compare the handbook's candidate rules: strip the prefix and match on digits; match on amount and date within two days; then use agreement between both as a higher-confidence match while flagging disagreements. Measure collisions before choosing a rule, and retain exact-reference matching as the baseline.
3. Build a left-side invoice bridge and a reverse captured-payment unmatched view. Report both row counts and INR amounts before and after each join, guarding against multiple attempts per invoice.
4. Separate failed attempts from captured receipts and classify valid post-quarter captures using the agreed quarter cutoff and timestamp in Asia/Kolkata.
5. Reconcile gateway captured amounts to settlement gross, fees, tax and expected net by settlement ID/date. Confirm whether cash-labeled gateway rows represent the full clinic cash-deposit source.
6. Give Finance an auditable list of unmatched invoices, unmatched captured payments, ambiguous references and late payments; present only aggregate outputs publicly.

## Reproducibility

The finance-only cleaner is [`clean_brief_c.py`](../clean_brief_c.py). From the repository root, run it against the full local source pack:

```powershell
python clean_brief_c.py --source-dir "<path-to-full-data-pack>" --output-dir data/clean/brief_c
```

The repository contains the cleaner and aggregate profile artifacts. Row-level finance CSVs and detailed exception lists stay local under `data/clean/brief_c/` per the starter kit's clean-data policy. The full cleaned output and its source row provenance are reproducible from the script.
