# H1 test volume and booking-system migration

**Stage 1:** compare H1 test volume with plan, then use the migration comparison as a diagnostic. The exact metric and the full city, month and channel breakdown are in [`project-analysis.md`](project-analysis.md).

## H1 result

The comparison is January–June 2026 against January–June 2025 only. Both actual and planned growth use the **436,094 H1 2025 active test lines** as the baseline, not full-year 2025. The primary count excludes 3,541 H1 2026 test lines on superseded records marked `rescheduled`, following the booking identity rule in notebook 03; no H1 2025 test lines were marked `rescheduled`. Active booked test lines grew to **451,332** in H1 2026 (**+3.49%**). The six-city plan was **515,740** (**+18.26%** implied growth), so actual volume reached **87.51% of plan** and missed by **64,408 lines**.

Keeping the rescheduled records would give 454,873 lines and +4.31% growth. That sensitivity is not the chosen measure because it counts old and replacement booking records for rescheduled visits.

## Migration comparison

| Group | H1 2025 | H1 2026 active | H1 plan | Attainment |
|---|---:|---:|---:|---:|
| Chennai and Jaipur (Nova migration) | 125,349 | 119,362 | 146,284 | 81.6% |
| Ahmedabad, Bengaluru, Hyderabad and Pune (legacy) | 310,745 | 331,970 | 369,456 | 89.9% |

The treated cities were already down **3.2%** year over year in January–March, compared with **+9.6%** for controls. In April–June they were down **6.4%** versus **+4.0%**. The pre-adjusted relative change is **+2.3 percentage points**, but the comparison is descriptive: only two cities migrated and the pre-period trends differed. It does not identify a causal migration effect.

## Additional checks

- Clinic lines fell **37,189 (12.96%)** across the six cities; home lines rose **52,427 (35.17%)**. Home growth partly offset clinic decline.
- Every city and month missed plan. June had the largest monthly shortfall (**16,015 lines**) and was the only month below its 2025 level.
- Nova-era collection coverage was **22,856/25,023 bookings (91.3%)**; result matches were **45,056/58,877 test lines (76.5%)**. Legacy result matches were 82.0% in the control cities and 82.3% in the treated cities. These joins use different grains and are not completion rates.

The files locate the shortfall and show a channel mix shift, but do not establish why clinic volume fell or why the plan was missed. Check the plan definition, local clinic capacity and demand, June performance, and booking-to-result timing before naming a cause.

## Reproducibility

```powershell
python analyze_h1_volume.py --data-dir "<path-to-full-cleaned-folder>" --output-dir outputs
python analyze_brief_a_b_migration.py --data-dir "<path-to-full-cleaned-folder>" --output-dir outputs
```

The outputs contain aggregate counts only. The full cleaned tables remain local.
