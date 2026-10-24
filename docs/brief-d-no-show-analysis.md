# Brief D: Is one clinic's no-show rate genuinely worse?

**Status:** Exploratory H1 2026 check; no clinic is established as a statistically worse outlier. Brief C is the final board-facing focus.

**Period and grain:** appointments with a slot date from 1 January through 30 June 2026; one distinct booking ID per appointment.

## Business answer

Among 189,191 bookings with a recorded `collected` or `no_show` outcome, 26,502 were no-shows: **14.01% overall**. JAI-05 has the highest raw clinic rate at **17.53% (27/154)**, but the interval is wide (95% Wilson: 12.34%–24.31%) and its case-mix-conditional one-sided shuffle p-value is 0.128. CHE-03 has the largest conditional excess statistic: **16.12% (975/6,049)** against a same-mix peer expectation of **15.18%**, a **0.94 percentage-point** difference. Its unadjusted conditional p-value is 0.021, but after comparing the largest statistic across all 31 clinics, the max-statistic adjusted p-value is **0.538**.

Therefore, the data do **not establish that any clinic is genuinely worse** after accounting for appointment mix and the fact that management scanned many clinics. JAI-05's high percentage is compatible with substantial sampling variation. CHE-03 merits follow-up because it has a large volume and an elevated raw rate, but its observed excess is also compatible with chance under the all-clinic reference.

**Disposition:** Brief D did not identify a dependable clinic-level performance issue and does not explain Brief A's 4.3% actual growth against 18.3% implied plan growth. The team selected Brief C as the final board-facing focus. CHE-03's outcome-capture gap remains a separate follow-up if those records are reconciled.

There is a material outcome-capture limitation: **7,283 of 196,474 rostered bookings (3.71%)** have no usable collection outcome. They are not labelled no-shows. The outcome is especially incomplete at CHE-03 after the booking-system transition, so the comparison is not fully conclusive until that data gap is reconciled.

## Definition and method

The handbook definition is applied at booking level: a booking is a no-show when its collection outcome is explicitly `no_show`; `collected` is the other observed outcome. A booking with no linked collection row, or a status outside those two values, is retained in the roster and counted as unknown. Bookings with no nonblank test code or a slot date outside H1 2026 are outside this analysis.

The primary rate denominator is the number of bookings with one of the two usable outcomes. Each clinic row reports its no-show count and known-outcome denominator. The chart uses 95% Wilson intervals to show raw-rate uncertainty. The CSV also gives a sensitivity range using every rostered booking: the lower endpoint treats unknowns as not no-shows; the upper endpoint treats all unknowns as no-shows. These endpoints are bounds, not assumptions about what actually happened.

For a fairer clinic comparison, bookings are grouped by appointment month, channel, number of test lines (1, 2, or 3+), time band, and weekday/weekend. Each clinic's observed outcomes are compared with other clinics in the same strata and weighted by that clinic's mix. A conditional hypergeometric shuffle keeps the observed number of no-shows and clinic booking sizes fixed in each stratum. The one-sided statistic asks whether a clinic is unusually high. The max-statistic p-value compares each clinic's statistic with the largest statistic across all 31 clinics in each shuffle, addressing the risk of finding a high clinic simply by scanning many clinics. This controls the clinic scan under the chosen strata; it does not correct outcome-recording bias or prove causation.

The analysis uses 5,000 shuffles with seed `20261023`. Its smallest possible nonzero Monte Carlo p-value is approximately 0.0002; p-values near the decision boundary should be rerun with more shuffles. No result here is near that boundary after max adjustment.

## Results that matter

| Clinic | City | No-shows / known outcomes | Raw rate (95% Wilson interval) | Unknowns | All-roster sensitivity range | Same-mix peer rate | Difference | Raw shuffle p | Max-adjusted p |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| JAI-05 | Jaipur | 27 / 154 | 17.53% (12.34%–24.31%) | 11 | 16.36%–23.03% | 14.59% | +2.94 pp | 0.128 | 0.998 |
| CHE-03 | Chennai | 975 / 6,049 | 16.12% (15.21%–17.07%) | 354 | 15.23%–20.76% | 15.18% | +0.94 pp | 0.021 | 0.538 |

The top raw-rate clinic and the largest conditional statistic are different clinics. That is why a percentage alone is not enough: JAI-05 has a small denominator, while CHE-03 has a much larger volume and a more modest excess after case-mix comparison. CHE-03's clinic-channel rate is 19.67% versus 11.87% for its home-channel bookings; this is a useful operational segmentation, not a causal comparison. Time-of-day and weekday splits are available in `brief_d_case_mix.csv` and should be used to form follow-up questions, not to select a preferred narrative after looking at the data.

## Connection to Briefs A and B

Brief A found that H1 test-line growth was 4.3% against an implied plan growth of 18.3%, with clinic test lines down 17.4% and home lines up 27.9% in Chennai and Jaipur combined. Brief B located a booking-system transition in those cities. Brief D follows a different step in the service funnel: whether a booked appointment has a recorded sample collection outcome. This lets the team ask whether volume mix and capture completeness could help explain why booked test-line growth and completed collection outcomes diverge.

CHE-03 illustrates why the briefs should be read together. Its known-outcome no-show rate is 15.67% on legacy bookings (500/3,190) and 16.61% on Nova bookings (475/2,859), while bookings without a usable outcome rise from 79/3,269 (2.4%) to 275/3,134 (8.8%). This is a stronger warning about **measurement completeness** than about no-show performance. It is consistent with the lower Nova-era collection-join coverage already flagged in the A/B analysis, but it does not establish a system effect: the period is short, this is one clinic, and unknown outcomes may be nonrandom. JAI-05 is also small: only 154 bookings have known outcomes across H1, with 11 additional unknowns.

## Next checks before an operational conclusion

1. Reconcile the 7,283 unknown bookings to collection and booking-system event logs, prioritizing CHE-03 April–June and checking whether missingness follows the Nova migration.
2. Confirm that every `no_show` and `collected` status follows the handbook definition, and that multi-test bookings still represent one visit outcome.
3. Review CHE-03's appointment-slot and clinic-channel operations with denominators shown; compare comparable strata and months.
4. Rerun after outcome reconciliation. If management needs a stronger significance claim, increase the shuffle count and pre-specify the clinic and comparison before looking at the next period.

## Reproducibility and outputs

The full cleaned data remains outside this repository. Install NumPy and Matplotlib, then run from the repository root:

```powershell
python analyze_brief_d_no_shows.py --data-dir "<path-to-full-cleaned-folder>" --output-dir outputs/brief_d --permutations 5000 --seed 20261023
```

Aggregate files and their grains are listed in [`outputs/README.md`](../outputs/README.md). The script does not write booking identifiers into the repository outputs. This is an initial analysis; review the code and validate the status mapping before presenting it as a final operational conclusion.
