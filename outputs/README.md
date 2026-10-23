# Brief A/B summary outputs

These compact CSVs were generated from the full local cleaned tables by `analyze_brief_a_b_migration.py`. The underlying patient-level and booking-level data are not included here.

| File | Grain | Contents |
|---|---|---|
| `brief_a_h1_overall.csv` | Six-city H1 total | Actual growth, implied plan growth, attainment and variance |
| `brief_a_b_city_summary.csv` | City | H1 test lines, year-over-year change, plan attainment and variance |
| `brief_a_b_group_plan.csv` | Treated/control group | H1 actual versus plan |
| `brief_a_b_period_summary.csv` | Group and Jan–Mar/Apr–Jun period | Matched-year growth, post gap and descriptive difference-in-differences |
| `brief_a_b_monthly_treated.csv` | Migration city-month | Matched-year counts, plan gap, channel counts and source-system mix |
| `brief_a_b_channel_summary.csv` | Dimension and category | H1 clinic/home and app/phone/walk-in counts |
| `brief_a_b_join_diagnostics.csv` | Year, group and source system | Booking-level collection joins and test-line-level result joins |

Regenerate with the command in [`docs/brief-a-b-analysis.md`](../docs/brief-a-b-analysis.md). The input directory must contain the cleaned CSV tables. These aggregate files contain no patient names or patient IDs.
