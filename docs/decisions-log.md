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
| A0 | H1 volume baseline | Compare active nonblank booking-test lines created January through June 2026 with the same months in 2025; sum all six cities' plan targets | Same-season periods and the plan's test-line measure share the same grain | 451,332 vs 436,094 is +3.49%; 515,740 planned is +18.26%; 64,408 lines below plan. Unfiltered growth is +4.31%, including 3,541 superseded rows |
| A1 | Test-volume grain | Count nonblank booking-test lines by `created_at` month and exclude `booking_status = rescheduled` | A rescheduled Nova booking has a replacement record; keeping the old line would count the same visit twice | This is active booked volume, not necessarily completed volume; confirm the plan?s definition |
| A2 | Comparison period | Compare Jan–Jun 2026 with Jan–Jun 2025, split into Jan–Mar and Apr–Jun | Compares the same seasonal months while examining migration timing | Only three post months are available |
| A3 | Migration/control groups | Treated = Chennai and Jaipur; controls = Ahmedabad, Bengaluru, Hyderabad and Pune | Source-system field shows Nova activity in March, nearly all test lines in April and all in May–June; other cities remain legacy | Migration is not randomized and cities may have concurrent shocks |
| A4 | Cross-table denominators | Collection joins are booking-level; result joins are booking-test-level | Collections have no test code; results do | These are join indicators, not completion rates without further reconciliation |
| A5 | Causal interpretation | Show the post-period growth gap and pre-period-adjusted descriptive estimate | The treated group already had a different pre-period trend | +2.3 percentage points is descriptive, not a causal effect |

## Cold runs

| Date | Who ran it | Fresh Codespace? | Runtime | Headline number | Same as last run? | If not, why |
|---|---|---|---|---|---|---|
| | | | | | | |

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

## Brief C reconciliation decisions (2026-10-24)

| # | Analysis choice | Decision | Rationale | Effect / caveat |
|---|---|---|---|---|
| C9 | Quarter and cutoff | Use Q2 2026 provisionally; define close as 30 June 23:59 IST and observe late captures through 15 July IST | Project context is H1 2026 and the latest supplied payment timestamp falls on 15 July in India time | Sponsor must confirm the year; the original request only says Q2 |
| C10 | Reference match | Exact invoice ID, then hyphen removal only when the canonical key uniquely identifies one invoice | Separator-free references are a repeated source format; amount/date similarity can mispair visits | 468,742 of 473,507 gateway attempts mapped; 4,765 remained unmatched with no fuzzy repair |
| C11 | Collection amount | Sum all captured attempts per invoice by cutoff; exclude failed attempts | Failed rows are not receipts; attempt grain must be kept visible | 71,211 matched captured rows total ₹119,265,677 across 70,902 Q2 invoices at close |
| C12 | Outstanding balance | Report positive invoice balances and overcaptures separately | Netting unrelated invoices could conceal balances or improperly apply credits | ₹14,104,863 positive balances across 8,356 invoices; ₹523,266 overcapture across 318 invoices, shown separately |
| C13 | Settlement comparison | Reconcile captured attempts to settlement gross by settlement ID as a diagnostic only | Payment and settlement dates differ, and independent bank/cash evidence is absent | Q2 linked captures exceed settlement gross by ₹2,979,412.02; Finance must resolve before bank-cash claims |
