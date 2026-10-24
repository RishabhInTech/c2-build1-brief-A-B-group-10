# Project charter · Brief C · Group 10

**Draft updated:** 2026-10-24 · **Status:** team/COO review pending

| | |
|---|---|
| Project | Build 1 · Data to Insight in Kalpa Health · Brief C: Money |
| Sponsor | Dr Priya Menon, COO, Kalpa Health |
| Reviewers | Finance controller; finance operations/payment owner |
| Group | 10: Rishabh and teammates (names to be completed by the group) |
| Repository | [Rishabh branch](https://github.com/RishabhInTech/c2-build1-brief-A-B-group-10/tree/Rishabh) |
| Working days | Three to four, per the handbook; presentation date to be confirmed |
| Charter updated on | 2026-10-24 |

## 1. The question, in the sponsor's words

> “Which invoices were never paid, which payments match no invoice, and how much of the gap is only timing?”

## 2. The question, in ours

Build a traceable bridge from invoice billing to captured payments and bank settlements. The bridge must distinguish unpaid invoices as of a stated cutoff, captured gateway payments with no invoice match, failed attempts, and cash/payment timing across the selected quarter boundary so Dr Menon can give Finance a concrete investigation list.

## 3. The deliverables

| # | Deliverable | Form | Acceptance test |
|---|---|---|---|
| D1 | The claim | One sentence on slide 3, with selected quarter, INR amount, counts and cutoff | Dr Menon can explain the bridge composition and action without implying unmatched means permanently lost. |
| D2 | The evidence | Notebooks 01–06 running cold; a SQL bridge Finance can rerun; aggregate profile/bridge outputs | A teammate reproduces the agreed counts and amounts from the repository workflow and local full data. |
| D3 | The audit trail | Approach, decisions, challenges and AI logs; row-count reconciliation | Every bridge bar traces to input rows and every rule has an alternative, reason and effect. |
| D4 | The action | Slide 6 plus finance exception lists | Finance receives invoice/payment references with source provenance, separated by action type. |
| D5 | The write-ups and video | `docs/writeups.md`, video link in README | Each member writes their own section and presents a defensible part. |

## 4. Targets

| Target | Measure | Owner |
|---|---|---|
| T1 Reconcile the stated quarter | Invoice and captured-payment counts and rupee amounts balance to matched + unmatched | Analysis owner to be assigned |
| T2 One sentence | Slide 3, with quarter, cutoff, denominator and caveat | Team |
| T3 Auditable | Decisions/logs account for every source row and join | Scribe to be assigned |
| T4 Reproducible | Fresh Codespace run in under ten minutes, subject to full-data volume | Cold-run owner to be assigned |
| T5 Defended | Any member can explain the ID rule, timing bar and cost of being wrong | All members |

## 5. Scope

| In | Out |
|---|---|
| Invoice, gateway attempt and settlement feeds; invoice reference mapping; captured/failed status; quarter timing; gross, fee, tax and net; actionable exceptions. | Clinical outcomes and patient-level features; they do not answer the financial bridge. |
| Adjacent periods needed to observe late payments and settlements. | Final accounting/audit sign-off without Finance confirming bank and clinic cash coverage. |
| Earlier A/B analyses as exploratory context. | Treating descriptive operational comparisons as proof of a financial cause. |

## 6. Roles and parts

| Member | Part owned | Notebooks | Also responsible for |
|---|---|---|---|
| Rishabh | Initial finance-only cleaning and repository workflow (confirm with team) | 01–03 (proposed; confirm) | Presenting the source profile and explaining cleaning decisions |
| Teammate names/roles | To be assigned by the group | To be assigned | Review mapping, bridge, SQL and finance exception lists |

## 7. Risks, and what we do about them

| Risk | Likelihood | Impact | What we do |
|---|---|---|---|
| Wrong invoice-reference rule | High: 95,921 gateway references failed the current dominant-format check | Captured money may appear unmatched or be paired incorrectly | Preserve raw/normalized refs; compare explicit rules; log collisions and unmatched rows before choosing. |
| A join multiplies payment attempts | Medium | Invoice or payment amounts are overstated | State each table's grain; show counts before/after; aggregate at the intended key and validate join cardinality. |
| Quarter year or cutoff is wrong | Open | Timing and “unpaid” totals change | Confirm quarter year and collection cutoff with the team/COO before the bridge. |
| Late payment is called unpaid | High near quarter close | Finance is given a false delinquency list | Include adjacent payment/settlement dates and define the observation cutoff. |
| Cash method feed is incomplete | Open | Collections are understated | Confirm whether the supplied cash-labeled attempts cover clinic deposits; request bank/cash register evidence if available. |
| Settlement gross is compared with gateway net | Medium | Fees/tax look like missing money | Reconcile gross, fee, tax, net and settlement date separately. |
| Full finance rows are committed publicly | Low with controls | Exposes transaction/booking identifiers and bloats repository | Keep row-level outputs local under `data/clean/brief_c/`; commit code and aggregate artifacts only. |

## 8. Assumptions we are making

| Assumption | What would prove it wrong | Where it appears if it does |
|---|---|---|
| Brief C's “second quarter” means a quarter represented in the released invoice files, likely 2026 Q2 given the H1 2026 project context. | COO/team selects Q2 2025 or another period. | Project statement, bridge parameters, slide 3. |
| One invoice is expected per visit. | Multiple invoice IDs share a booking ID or source owner documents split invoices. | `outputs/brief_c/finance_profile.json`, decisions log, bridge grain. |
| `captured` is the gateway status that represents successful collection for the gateway-side bridge. | Finance/vendor defines another settled/paid status or later reversal. | Status mapping, bridge query and caveat. |
| The supplied gateway cash method includes some cash-related records. | Finance says clinic cash deposits are tracked in a separate register or bank batch. | Source coverage and unmatched/coverage caveat. |

## 9. Decision rights

| Decision | Who makes it | By when |
|---|---|---|
| Invoice-reference mapping and grain | Analysis team, reviewed by Finance controller | Before bridge freeze |
| Quarter year and observation cutoff | Dr Menon/Finance controller with team | Before quarter-level calculations |
| Headline claim and action | Team proposes; COO approves | Before final presentation |
| Freeze | Group | Evening before presentation |

## 10. Changes

| Date | What changed | Why | Who |
|---|---|---|---|
| 2026-10-24 | Selected Brief C as the final board-facing brief after reviewing the project question and source coverage. | Brief C asks for an auditable money bridge directly for the COO and Finance. | Rishabh (team decision; confirm group members) |
