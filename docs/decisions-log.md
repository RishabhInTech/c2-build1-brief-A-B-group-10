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

## Brief D analysis decisions (2026-10-23)

| # | Analysis choice | Decision | Rationale | Effect / caveat |
|---|---|---|---|---|
| D1 | No-show definition | Count explicit `no_show`; use explicit `collected` as the other known outcome; retain no-row or unrecognized statuses as unknown | The handbook outcome is a booking where no sample was collected; absence of an event row is not proof of a no-show | Primary rates use 189,191 known outcomes; 7,283 unknowns are separately reported |
| D2 | Appointment grain and dates | One distinct booking ID with a nonblank test code and H1 2026 `slot_at` | One visit can contain several test lines but has one collection outcome; appointment slot dates align the outcome question | Test count per booking is used as a case-mix factor; status and event reconciliation remain important |
| D3 | Clinic fairness and chance | Compare within month/channel/test-count/time/day-type strata; run conditional hypergeometric shuffles and adjust against the maximum across 31 clinics | This accounts for observed appointment mix and the multiple-clinic scan | No clinic is a statistically established high outlier; this does not fix unknown-outcome bias |
| D4 | Brief A/B connection | Compare known-outcome no-show rates and missing outcomes by month and source system | Separates appointment outcome from the volume metric and exposes a possible migration-era capture issue | CHE-03 unknowns are 2.4% on legacy vs 8.8% on Nova rostered bookings; this is an association, not causation |

## Brief C cleaning decisions (2026-10-24)

The detailed machine-readable log is generated in the local finance-only pack. It includes source file/row provenance. This repository commits the decisions and aggregate exception counts, not the row-level invoice/payment CSVs.

| # | Cleaning choice | Decision | Rationale | Effect / caveat |
|---|---|---|---|---|
| C1 | Finance scope | Clean invoices, gateway attempts and settlements only | These are the Brief C money-bridge source tables | Existing `cleaned/` pack is unchanged; 470,776 invoices, 473,507 attempts and 562 settlements retained |
| C2 | Period | Retain every supplied finance period | The brief names Q2 but not a year; adjacent payments/settlements are needed to measure timing | Confirm Q2 year and cutoff with team/Finance before bridge calculations |
| C3 | Currency | Keep invoice amounts in INR; convert gateway/settlement paise with `Decimal` to two-decimal INR | Prevent float rounding and make table amounts comparable | No invalid or blank amount values found in these inputs |
| C4 | Reference normalization | Trim and uppercase gateway invoice refs; preserve raw and normalized values | Safe normalization is reversible; stripping separators or fuzzy matching could collide | 95,921 non-dominant format references are retained and summarized; no guessed matches are made |
| C5 | Payment attempts and duplicates | Retain captured and failed attempts and all repeated keys; flag duplicates instead of deleting | Multiple attempts per invoice can be legitimate, and status determines whether money was captured | No duplicate invoice IDs, payment IDs, or settlement IDs were found; invoice references repeat by design |
| C6 | Timing | Preserve epoch and add UTC and Asia/Kolkata timestamps | Quarter boundary should be assigned consistently in local time, with source time auditable | Payments are present through July 2026 and settlements through Q3 2026 |
| C7 | Personal data and traceability | Omit patient name/ID; retain booking ID and source file/row | Booking helps validate one invoice per visit; provenance supports finance review | Row-level outputs stay local and ignored by Git; aggregate profile is committed |
| C8 | Identifier format checks | Validate payment IDs as hexadecimal suffixes, not digits only | The actual gateway ID family contains `a`–`f`; the first overly strict check falsely flagged these valid IDs | Corrected the format rule; remaining quality exceptions are invoice-reference variants |
