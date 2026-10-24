# Assistant log · Brief C · Group 10

Record each material assistant use, including reviewed code, analysis and documentation.

| # | Date | Who | Tool | What we asked (one line) | What we did with the answer |
|---|---|---|---|---|---|
| 1 | 2026-10-23 | Rishabh | OpenAI Codex | Asked for a quality review of the cleaning and reconciliation before analysis. | Used the review to check source hashes, retained exceptions and cross-table joins; still responsible for verifying and explaining the cleaning decisions. |
| 2 | 2026-10-23 | Rishabh | OpenAI Codex | Asked for Brief A city/channel analysis and a comparison with Brief B's Chennai/Jaipur booking-system migration, including runnable Python. | Reviewed the metric, treated/control groups, pre/post comparison, denominator correction and caveats; will verify and explain the results to the team. |
| 3 | 2026-10-23 | Rishabh | OpenAI Codex | Asked for help preparing the analysis code, aggregate outputs and related documentation for the GitHub repository. | Used the generated script and documentation as a draft; full data remains outside the repo, and the team will review the committed artifacts. |
| 4 | 2026-10-24 | Rishabh | OpenAI Codex | Asked for a finance-only cleaning workflow and reproducible invoice-to-capture analysis for the COO's question. | Used the cleaning and reconciliation scripts as drafts; checked the reference rule, row counts, cutoff, balances and settlement differences against the supplied full data. The team must confirm H1 source coverage and defend the bridge. |
| 5 | 2026-10-24 | Rishabh | OpenAI Codex | Asked to check H1 2026 test-volume growth against plan before presenting the finance bridge, and to explain the shortfall. | Found superseded reschedule lines in the original count; excluded 3,541 per the booking identity rule, retained the raw count as a sensitivity, and recomputed city, month, channel and migration cuts. The available files identify patterns, not a causal root cause. |
