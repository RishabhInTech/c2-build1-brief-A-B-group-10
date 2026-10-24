# Project analysis: volume first, money next

## 1. H1 test-volume check

**No: on the active-booking definition, H1 2026 booked test lines grew 3.49%, not 5%.** The earlier unfiltered count was 4.31%, but it included 3,541 test lines on records marked `rescheduled`. The project’s booking rule says Nova creates a replacement booking and marks the old record `rescheduled`; the old line should not be counted again. We exclude those superseded lines and keep the unfiltered total as a sensitivity figure.

After that adjustment, H1 2026 has **451,332** active test lines versus **436,094** in H1 2025, up **15,238**. The 2026 six-city plan is **515,740** lines, equivalent to **18.26% growth** over the 2025 baseline. Actual volume reached **87.51% of plan** and finished **64,408 lines short**, a **14.77 percentage-point** gap between actual and implied plan growth.

The measure counts one row per booking-test line with a nonblank `test_code`, grouped by `created_at` month, across Ahmedabad, Bengaluru, Chennai, Hyderabad, Jaipur and Pune. It compares January–June 2026 with January–June 2025 only. Both actual growth and plan growth use the **436,094 active H1 2025 lines** as their denominator; neither uses full-year 2025. It excludes `booking_status = rescheduled` from H1 2026 per the booking identity rule in notebook 03. No H1 2025 test lines were marked `rescheduled`, so the adjustment affects only the 2026 count. The target is the sum of the six cities' January–June monthly targets in `plan_2026_h1.csv`.

```text
Active H1 2026 lines = 454,873 raw lines − 3,541 superseded reschedule lines = 451,332
Actual growth = (451,332 / 436,094 − 1) × 100 = 3.49%
Plan growth   = (515,740 / 436,094 − 1) × 100 = 18.26%
Plan attainment = 451,332 / 515,740 × 100 = 87.51%
Shortfall = 451,332 − 515,740 = −64,408 test lines
Sensitivity: 454,873 / 436,094 − 1 = 4.31% if rescheduled rows are retained
```

Reproduce the primary counts and city/month/channel tables with `analyze_h1_volume.py` using the full cleaned folder:

```powershell
python analyze_h1_volume.py --data-dir "<path-to-full-cleaned-folder>" --output-dir outputs
```

Confirm with the plan owner that targets mean active booked test lines. If the plan instead counts all booking records or completed lab tests, the denominator and outcome definition must be aligned before board use.

### Where the plan gap sits

All six cities finished below plan. Chennai has the largest shortfall after removing superseded rows; Jaipur has the lowest attainment and the largest year-over-year decline.

| City | H1 2025 lines | H1 2026 active lines | YoY growth | Plan | Attainment | Lines below plan |
|---|---:|---:|---:|---:|---:|---:|
| Ahmedabad | 76,910 | 83,770 | +8.92% | 90,773 | 92.29% | 7,003 |
| Bengaluru | 100,007 | 106,058 | +6.05% | 120,085 | 88.32% | 14,027 |
| Chennai | 80,292 | 79,671 | −0.77% | 93,912 | 84.84% | 14,241 |
| Hyderabad | 73,117 | 77,533 | +6.04% | 86,421 | 89.72% | 8,888 |
| Jaipur | 45,057 | 39,691 | −11.91% | 52,372 | 75.79% | 12,681 |
| Pune | 60,711 | 64,609 | +6.42% | 72,177 | 89.51% | 7,568 |
| **All cities** | **436,094** | **451,332** | **+3.49%** | **515,740** | **87.51%** | **64,408** |

The monthly view misses plan in every month. June has the largest gap at 16,015 lines and is the only month below its 2025 level: 68,254 versus 70,892, down 3.72%. See [`brief_a_h1_monthly.csv`](../outputs/brief_a_h1_monthly.csv) and [`brief_a_b_city_summary.csv`](../outputs/brief_a_b_city_summary.csv).

### What changed in the volume mix

| Channel | H1 2025 | H1 2026 active | Change | YoY |
|---|---:|---:|---:|---:|
| Clinic | 286,997 | 249,808 | −37,189 | −12.96% |
| Home | 149,097 | 201,524 | +52,427 | +35.17% |
| **Total** | **436,094** | **451,332** | **+15,238** | **+3.49%** |

Clinic lines fell in every city while home lines rose in every city. The home increase partly offset the clinic decline, leaving modest net growth. This identifies the mix behind the total; it does not establish why clinic volume fell or whether the plan's channel assumptions were realistic. City-channel details are in [`brief_a_h1_channel_by_city.csv`](../outputs/brief_a_h1_channel_by_city.csv).

### What the migration check can and cannot say

The two cities that migrated to Nova reached 81.6% of plan; the four cities remaining on legacy reached 89.9%. The migration group was already down 3.2% year over year in January–March while the comparison group was up 9.6%. In April–June, the groups were down 6.4% and up 4.0%, respectively. The relative gap improved by 2.3 percentage points after March, but only two cities migrated and their pre-period trend differed. This comparison cannot establish that Nova caused the H1 plan miss.

Collection and result joins are coverage diagnostics at different grains, not completed-test rates. Nova-era result matching is lower than legacy matching; timing and mapping need review before treating it as missing volume. The metric here is booked test lines, not lab-completed tests. If the plan tracks completed tests, agree a result-date definition and recalculate before replacing this baseline.

**What we can conclude:** active H1 booked volume grew 3.49%, well below the plan's implied 18.26%; all cities and months missed their targets, with clinic-line declines partly offset by home growth. **What we cannot conclude from these files:** the causal business reason for the clinic decline or plan miss. Next checks are June and Chennai clinic demand, local capacity and marketing, plan assumptions, and booking-to-result coverage.

## 2. Finance bridge

After the volume check, the project answers the COO's money question: which Q2 invoices had no captured match, which captures lacked an invoice match, and how much changed after quarter close. The provisional Q2 2026 bridge, matching rule, settlement gap and Finance action lists are in [`brief-c-analysis.md`](brief-c-analysis.md).
