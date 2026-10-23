# Brief A and Brief B: test volume and booking-system migration

**Status:** Exploratory background analysis; Brief C is the final board-facing focus

**Analysis period:** January–June 2025 and January–June 2026

**Volume unit:** one booking-test line with a nonblank test code

**Migration cities:** Chennai and Jaipur; Nova appears in March 2026, is nearly complete in April and accounts for all counted test lines in May–June
**Comparison cities:** Ahmedabad, Bengaluru, Hyderabad and Pune, which remain on legacy

## Question

Brief A asks why test volume grew far below the plan. Brief B concerns the booking-system change in Chennai and Jaipur. This analysis tests whether the migrated cities’ volume pattern changed around the migration, using the four legacy cities as a descriptive comparison.

## Headline

Across all six cities, H1 2026 volume was **454,873 test lines**, up **4.3%** from **436,094** in H1 2025. The six-city H1 plan totals **515,740**, equivalent to **18.3% growth** over H1 2025. Actual volume reached **88.2% of plan**, a shortfall of **60,867 test lines**. The growth gap between actual and implied plan growth is about **14.0 percentage points**.

The two migration cities together reached **84.0% of plan**; the four legacy cities reached **89.9%**. Both groups missed plan, and the migration cities’ H1 outcomes differ substantially: Chennai grew 2.1% year over year, while Jaipur declined 9.2%.

## City results

| City | Group | H1 2025 test lines | H1 2026 test lines | YoY change | H1 2026 plan | Attainment | Variance |
|---|---|---:|---:|---:|---:|---:|---:|
| Ahmedabad | Legacy | 76,910 | 83,770 | +8.9% | 90,773 | 92.3% | -7,003 |
| Bengaluru | Legacy | 100,007 | 106,058 | +6.1% | 120,085 | 88.3% | -14,027 |
| Chennai | Migration | 80,292 | 82,002 | +2.1% | 93,912 | 87.3% | -11,910 |
| Hyderabad | Legacy | 73,117 | 77,533 | +6.0% | 86,421 | 89.7% | -8,888 |
| Jaipur | Migration | 45,057 | 40,901 | -9.2% | 52,372 | 78.1% | -11,471 |
| Pune | Legacy | 60,711 | 64,609 | +6.4% | 72,177 | 89.5% | -7,568 |

## Before and after the migration

For a like-for-like comparison, January–March is treated as the pre-period and April–June as the post-period. The same months in 2025 provide the year-over-year baseline.

| Group and period | H1 2025 matching months | H1 2026 matching months | YoY growth |
|---|---:|---:|---:|
| Migration cities, Jan–Mar | 64,298 | 62,323 | -3.1% |
| Migration cities, Apr–Jun | 61,051 | 60,580 | -0.8% |
| Legacy cities, Jan–Mar | 156,952 | 171,960 | +9.6% |
| Legacy cities, Apr–Jun | 153,793 | 160,010 | +4.0% |

In April–June, migration-city growth was **4.8 percentage points below** legacy-city growth. The pre-period growth gap was already **12.6 points below** the controls. Subtracting the pre-period gap from the post-period gap gives a pre-adjusted difference in the YoY growth gap of **+7.8 percentage points**. This says the relative trend improved after March; it does not establish that Nova caused the improvement.

The comparison has important limits: only two cities migrated, the migration cities already had different pre-period trends, migration is not randomly assigned, and the post-period is only three months. It should be treated as a hypothesis check, not a causal estimate.

## What moved in the migration cities

Across Chennai and Jaipur combined, clinic test lines fell from **82,690** to **68,338** (**-17.4%**). Home test lines rose from **42,659** to **54,565** (**+27.9%**). The home increase offset much, but not all, of the clinic decline. App, phone and walk-in source counts each declined by about 2% in aggregate.

The city-specific pattern is mixed. Jaipur’s decline was already present in January–March, before Nova became the dominant source system: -12.3% in January, -16.1% in February and -15.2% in March. April was nearly flat year over year (-0.1%). Chennai grew in January and February, dipped in March, grew in April and May, then declined in June. That is not a uniform post-migration volume drop across both cities.

## Collection and result joins

These are reconciliation indicators with distinct denominators, not completion rates:

| Cohort | Bookings with collection row | Booking-test lines with matching result row |
|---|---:|---:|
| 2025 treated, legacy | 52,942 / 54,576 (97.0%) | 101,762 / 125,349 (81.2%) |
| 2026 treated, legacy | 24,960 / 25,738 (97.0%) | 49,801 / 60,485 (82.3%) |
| 2026 treated, Nova | 24,304 / 26,522 (91.6%) | 47,921 / 62,418 (76.8%) |
| 2026 control, legacy | 137,321 / 141,575 (97.0%) | 272,091 / 331,970 (82.0%) |

The lower Nova-era join rates make system capture or key-mapping problems worth checking. They could also reflect workflow, timing, or source coverage. A result row is matched using `(booking_id, test_code)`; a collection row is matched using `booking_id`. Unmatched rows documented in `cleaned/join_row_counts.csv` should be reviewed before these rates are interpreted operationally.

## Conclusion and next checks

The current evidence connects the briefs but does not support the claim that the booking-system migration caused the H1 growth shortfall. The migration cities did miss plan more severely as a group, but their relative trend improved after March and their city-level results diverge. Jaipur’s clinic decline began before the full migration; a broad clinic-versus-home shift appears in both migration cities; and the Nova-era join indicators are weaker.

Next, validate the migration timeline and booking-ID mapping with source-system owners; compare booked test lines with visit-level collections using correct grains; and inspect Jaipur clinic routine-test demand by month. Revisit the volume conclusion after separating true demand changes from capture and workflow changes.

## Reproducibility

The full cleaned source tables are not committed to this repository. Generate the compact CSV outputs from the full local cleaned directory with:

```powershell
python analyze_brief_a_b_migration.py --data-dir "<path-to-full-cleaned-folder>" --output-dir outputs
```

The script uses only Python’s standard library. Summary outputs are in [`outputs/`](../outputs/README.md). The cleaning and reconciliation decisions are recorded in the local `cleaned/decisions_log.csv` and `cleaned/join_row_counts.csv` artifacts; those full artifacts are not currently stored in this repository.
