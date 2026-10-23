# Decisions log · cleaning and reconciliation · Brief <LETTER> · Group <N>

Every act of cleaning is a decision with a reason and an effect. Input equals clean plus rejected, every time. The headline number is recomputed after every decision so the bridge from raw to final is visible.

## Reconciliation

| Step | Table | Rows in | Rows kept | Rows rejected | In = kept + rejected? | Headline number after this step | Owner | Date |
|---|---|---|---|---|---|---|---|---|
| 0 | raw as received | | | | | | | |
| 1 | | | | | | | | |

## Decisions

| # | Table | What we found | Decision (drop / default / keep and flag / map / split) | Reason | Rows affected | Effect on the headline | Reversible? | Owner |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

## Joins

| # | Left table (rows) | Right table (rows) | Key | Type | Rows after | Keys matched more than once | Explanation of the change in count | Owner |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

## Brief A/B analysis decisions (2026-10-23)

These are analysis choices, separate from the raw-to-clean reconciliation above. Source row accounting remains in `cleaned/input_clean_rejected.csv` in the full local data pack.

| # | Analysis choice | Decision | Rationale | Effect / caveat |
|---|---|---|---|---|
| A1 | Test-volume grain | Count one booking-test row for each nonblank test code, grouped by `created_at` month | Matches the plan's test-volume wording and the cleaned booking grain | Excludes blank test-code rows; this is booked volume, not necessarily completed volume |
| A2 | Comparison period | Compare Jan–Jun 2026 with Jan–Jun 2025, split into Jan–Mar and Apr–Jun | Compares the same seasonal months while examining migration timing | Only three post months are available |
| A3 | Migration/control groups | Treated = Chennai and Jaipur; controls = Ahmedabad, Bengaluru, Hyderabad and Pune | Source-system field shows Nova activity in March, nearly all test lines in April and all in May–June; other cities remain legacy | Migration is not randomized and cities may have concurrent shocks |
| A4 | Cross-table denominators | Collection joins are booking-level; result joins are booking-test-level | Collections have no test code; results do | These are join indicators, not completion rates without further reconciliation |
| A5 | Causal interpretation | Show the post-period growth gap and pre-period-adjusted descriptive difference-in-differences | The treated group already had a different pre-period trend | +7.8 percentage points is descriptive, not a causal effect |

## Cold runs

| Date | Who ran it | Fresh Codespace? | Runtime | Headline number | Same as last run? | If not, why |
|---|---|---|---|---|---|---|
| | | | | | | |
