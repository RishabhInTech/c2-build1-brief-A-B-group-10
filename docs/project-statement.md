# Project statement · Brief C · Group 10

**Status:** Brief C is the final board-facing focus, selected on 2026-10-24. Earlier A/B work remains supporting project context.

The analysis begins with the H1 test-volume plan check. Excluding 3,541 superseded reschedule lines, active booked test volume grew 3.49% against 18.26% implied plan growth. It then answers the COO's finance question with Brief C. See [`project-analysis.md`](project-analysis.md) for the calculation and its limits. The prediction below was recorded before invoice/payment matching and bridge analysis, not before any data was opened.

## 1. Dr Menon's words

> “Which invoices were never paid, which payments match no invoice, and how much of the gap is only timing?”

## 2. The question in our words

Dr Menon needs an auditable bridge from invoices raised to money collected, with counts and rupee amounts at every step. The COO should be able to distinguish unpaid invoices, captured payments that cannot be linked to an invoice, failed attempts, and payments or settlements recorded after the quarter boundary, then give Finance a review list.

## 3. The question she did not ask

Which year is the “second quarter,” and what payment/settlement cutoff should define “collected by quarter end”? The supplied files contain Q2 2025 and Q2 2026 invoices and payments after quarter-end; the year and cutoff can change both the unpaid list and the timing bar. Confirm these with the team and Finance before reporting a final gap.

## 4. Translation into the method

| Her words | Method | Where the vocabulary changes |
|---|---|---|
| “Invoices and collections disagree” | Reconciliation bridge | Invoice rows and payment-attempt rows have different grains; count and sum each separately. |
| “Which invoices were never paid?” | LEFT join / anti-join from invoices to eligible captured payments | “No matching payment row” is not automatically “never paid” until period cutoff, reference variants, and payment status are checked. |
| “Which payments match no invoice?” | Reverse anti-join from captured payments to invoices | Failed attempts are not collected money; repeated attempts must not be silently added as distinct receipts. |
| “How much is only timing?” | Compare invoice, capture, and settlement timestamps across a stated quarter boundary | A payment after the invoice quarter can be late collection rather than a permanent loss; settlement net also differs from gateway gross by fees and tax. |

## 5. What does not transfer from Retail

| In Retail | In a diagnostics business | What changes for our analysis |
|---|---|---|
| A missed sale costs one order. | A visit can create an invoice; payment attempts and bank settlements occur later and may be batched. | Reconcile visit invoices, captured attempts, and settlement batches as separate steps. |
| The shopper chooses the basket. | The patient may not select the clinically prescribed test basket or the invoice amount. | Do not interpret invoice amount changes as customer basket choices without clinical context. |
| A payment record is often treated as a sale. | A failed attempt, captured gateway payment, and bank settlement are different events. | Status and event time decide which bridge bar an amount belongs in. |

## 6. Our prediction, before the matching step

**Recorded 2026-10-24, after source profiling but before joins or bridge calculations:** we expect the observed gap to contain more than one component: invoice-reference variants and payment/settlement timing are plausible contributors, and some attempts will be failed or repeated. We expect not every rupee of the invoice-to-gateway difference to be an unpaid invoice. The bridge will test this; it is not a result.

## 7. Requirements

### Functional: what the analysis must do

| # | Requirement | How we will show it is met |
|---|---|---|
| F1 | Profile invoice, gateway-payment, and settlement sources before joining. | Counts, amount totals, date ranges, statuses, ID formats, duplicates and missingness are in the Brief C profile. |
| F2 | State and test an invoice-reference mapping rule. | Preserve source and normalized values; show match/unmatched counts and exceptions; compare alternatives in the approach log. |
| F3 | Build an invoice-to-collected bridge with counts and INR amounts on every bar. | Reconcile input invoices = matched + unmatched; separately reconcile captured payment attempts = matched + unmatched, with row counts before/after joins. |
| F4 | Separate nonpayment, unmatched captured payments, failed attempts, and quarter-boundary timing. | Actionable row lists and aggregate bridge bars trace to source file and row. |
| F5 | Explain the effect of settlement fees/tax and distinguish gateway capture from bank net. | Reconcile settlement gross, fees, tax and net separately; document any unreconciled bank/cash source. |

### Non-functional: how well it must do it

| # | Requirement | How we will show it is met |
|---|---|---|
| N1 | Re-run in a fresh Codespace without manual edits. | A teammate follows the README command and logs a cold run in `docs/decisions-log.md`. |
| N2 | Finance can audit each number back to source rows. | Keep source-file/row provenance in local cleaned tables and IDs in local exception/action lists; commit aggregate outputs only. |
| N3 | Every cleaning and join decision has a reason and measured effect. | Update `docs/approach-log.md` and `docs/decisions-log.md` before interpreting the result. |
| N4 | Keep row-level financial records out of the public repository. | Store generated finance CSVs under `data/clean/brief_c/` locally; Git ignores the row-level outputs. |

### Constraints: what we cannot change

| # | Constraint |
|---|---|
| C1 | Use the starter-kit workflow: notebooks, SQL, Python and GitHub; standard-library cleaning is already available. |
| C2 | The team reports that the instructor permitted AI assistance on 2026-10-23. Disclose assistant use in `docs/ai-log.md`; the team owns validation and defense. |
| C3 | Use the released data as supplied; do not invent missing payment rows or silently rewrite malformed identifiers. |
| C4 | A `cash` method label appears in the supplied gateway export, but no independent bank statement or clinic cash-deposit register has yet been validated; Finance must confirm coverage before sign-off. |

## 8. Scope

| In | Out, and why |
|---|---|
| Invoice rows, captured and failed gateway attempts, settlements, reference mapping, quarter timing, fees/tax, and finance action lists. | Patient-level identity or clinical outcomes; they are not needed to answer the money question. |
| Q2 bridge after the team/COO confirms the year and payment cutoff; adjacent periods are retained to measure late payments. | A claim that every unmatched invoice is permanently unpaid before the observation cutoff and finance source coverage are confirmed. |
| Earlier A/B work as documented exploration and context. | Reopening those analyses as the final board question unless new evidence or a team decision changes scope. |

## 9. Done looks like

A bridge from invoiced to collected in which every bar is a count and an amount, both sides reconcile, and Finance has a list to act on tomorrow. For this data, every bar will also name its grain, quarter, status rule, cutoff, and source rows; the bridge will separately show gateway fees/tax and payments that arrived after quarter close.

## 10. Who signs off

| Reader | What they will check | What would make them reject it |
|---|---|---|
| Dr Priya Menon, COO | One defensible sentence on the size and composition of the gap, with a recommended action. | A total without a period, denominator, timing rule, or action. |
| Finance controller | Every bridge count and amount reconciles to source rows and survives a re-run. | Hidden fan-out, failed attempts counted as receipts, or unexplained unmatched records. |
| Finance operations / payment owner | The unmatched and late-payment lists can be investigated by invoice/payment reference. | An action list without source provenance or a mapping rule they can validate. |

**Open team inputs:** confirm the Q2 year/cutoff, member names and roles, and the COO/Finance review date before the final bridge is presented.
