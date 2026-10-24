"""Assess clinic no-show rates using reconciled bookings and collections.

Run from the project root:
    python analyze_brief_d_no_shows.py --data-dir cleaned --output-dir outputs

One eligible appointment is one distinct booking_id with at least one
nonblank test code and a slot date in H1 2026. The primary rate uses bookings
with an explicit collection outcome (collected/no_show); bookings with no
usable collection outcome are shown separately and in a sensitivity range.
"""

import argparse
import csv
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np


PERIOD_START = "2026-01-01"
PERIOD_END = "2026-06-30"
RNG_SEED = 20261023
N_PERMUTATIONS = 20_000


def read_rows(data_dir, filename):
    with (data_dir / filename).open(encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def write_csv(path, records, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def resolve_data_dir(raw_path):
    if raw_path:
        path = Path(raw_path).expanduser().resolve()
        if not (path / "bookings.csv").exists():
            raise FileNotFoundError(f"No bookings.csv in data directory: {path}")
        return path
    root = Path(__file__).resolve().parent
    for candidate in (root / "cleaned", root / "data" / "clean"):
        if (candidate / "bookings.csv").exists():
            return candidate
    raise FileNotFoundError("Pass --data-dir with the reconciled cleaned CSV tables.")


def time_band(slot_text):
    value = slot_text.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    hour = dt.hour
    if hour < 9:
        return "before_09"
    if hour < 13:
        return "09_to_12"
    return "13_or_later"


def test_band(test_count):
    if test_count == 1:
        return "1"
    if test_count == 2:
        return "2"
    return "3_plus"


def wilson_interval(successes, total, z=1.959963984540054):
    if total == 0:
        return float("nan"), float("nan")
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * np.sqrt((p * (1 - p) / total) + z * z / (4 * total * total)) / denominator
    return 100 * (center - half), 100 * (center + half)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="folder containing cleaned CSV tables")
    parser.add_argument("--output-dir", default="outputs", help="aggregate output folder")
    parser.add_argument("--permutations", type=int, default=N_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    args = parser.parse_args()
    if args.permutations < 1:
        parser.error("--permutations must be at least 1")
    data_dir = resolve_data_dir(args.data_dir)
    output_dir = Path(args.output_dir).expanduser().resolve()

    # Build a booking-level roster and count distinct valid test lines per visit.
    appointments = {}
    for r in read_rows(data_dir, "bookings.csv"):
        slot = (r.get("slot_at") or "").strip()
        date_part = slot[:10]
        code = (r.get("test_code") or "").strip()
        if not code or not (PERIOD_START <= date_part <= PERIOD_END):
            continue
        bid = r["booking_id"]
        appointment = appointments.get(bid)
        if appointment is None:
            appointment = {
                "booking_id": bid,
                "clinic_id": r["clinic_id"],
                "city": r["city"],
                "channel": (r.get("channel") or "unknown").strip().lower(),
                "slot_at": slot,
                "source_system": r.get("source_system", ""),
                "test_count": 0,
                "year_month": date_part[:7],
            }
            appointments[bid] = appointment
        appointment["test_count"] += 1

    # The collection event is booking-level. Preserve missing rows as unknown.
    outcome = {}
    collection_clinic = {}
    for r in read_rows(data_dir, "collections.csv"):
        bid = r["booking_id"]
        if bid in appointments:
            outcome[bid] = (r.get("status") or "").strip().lower()
            collection_clinic[bid] = r.get("clinic_id", "")

    clinic_catalogue = {
        r["clinic_id"]: r for r in read_rows(data_dir, "clinics.csv")
    }
    outcomes = {"collected", "no_show"}
    cohort = {}
    for bid, a in appointments.items():
        status = outcome.get(bid, "missing_event")
        if status not in outcomes:
            status = "missing_event" if status == "" else f"unknown_status:{status}"
        a["outcome"] = status
        if bid in collection_clinic and collection_clinic[bid] != a["clinic_id"]:
            a["clinic_mismatch"] = 1
        else:
            a["clinic_mismatch"] = 0
        if status in outcomes:
            slot_dt = datetime.fromisoformat(a["slot_at"].replace("Z", "+00:00"))
            # The strata control for appointment mix without fragmenting the
            # data into too many tiny cells.
            a["stratum"] = (
                a["year_month"],
                a["channel"],
                test_band(a["test_count"]),
                time_band(a["slot_at"]),
                "weekend" if slot_dt.weekday() >= 5 else "weekday",
            )
            cohort[bid] = a

    if not cohort:
        raise ValueError("No H1 2026 bookings with collected/no_show outcome rows found.")

    # Summary denominators: all eligible appointments, known outcomes, and
    # missing event records are reported separately for every clinic.
    counts = defaultdict(Counter)
    stratum_counts = defaultdict(Counter)
    strata = defaultdict(list)
    for bid, a in appointments.items():
        counts[a["clinic_id"]][a["outcome"]] += 1
    for bid, a in cohort.items():
        clinic = a["clinic_id"]
        stratum = a["stratum"]
        label = 1 if a["outcome"] == "no_show" else 0
        stratum_counts[(clinic, stratum)]["n"] += 1
        stratum_counts[(clinic, stratum)]["no_show"] += label
        strata[stratum].append((clinic, label))

    clinics = sorted(counts)
    clinic_stats = {}
    for clinic in clinics:
        no_show = counts[clinic]["no_show"]
        collected = counts[clinic]["collected"]
        unknown = sum(value for status, value in counts[clinic].items() if status not in outcomes)
        eligible = no_show + collected
        roster_n = eligible + unknown
        rate = no_show / eligible if eligible else float("nan")
        lower, upper = wilson_interval(no_show, eligible)
        clinic_stats[clinic] = {
            "no_show": no_show,
            "collected": collected,
            "eligible": eligible,
            "unknown": unknown,
            "roster": roster_n,
            "rate": rate,
            "ci_low": lower,
            "ci_high": upper,
            "missing_rate": unknown / roster_n if roster_n else float("nan"),
            "lower_sensitivity": no_show / roster_n if roster_n else float("nan"),
            "upper_sensitivity": (no_show + unknown) / roster_n if roster_n else float("nan"),
        }

    # Case-mix standardization: compare each clinic with other clinics inside
    # the same month/channel/test-count/time/day-type strata, weighted by that
    # clinic's own observed case mix. Report unsupported appointments.
    std = {}
    observed_z = {}
    variances = {}
    for clinic in clinics:
        target_n = target_y = expected_y = supported_n = supported_y = 0
        score = variance = 0.0
        for stratum, entries in strata.items():
            n_c = stratum_counts[(clinic, stratum)]["n"]
            if not n_c:
                continue
            y_c = stratum_counts[(clinic, stratum)]["no_show"]
            n_all = len(entries)
            y_all = sum(y for _, y in entries)
            n_peer = n_all - n_c
            y_peer = y_all - y_c
            target_n += n_c
            target_y += y_c
            if n_peer > 0:
                peer_rate = y_peer / n_peer
                expected_y += n_c * peer_rate
                supported_n += n_c
                supported_y += y_c
            if n_all > 1:
                p_all = y_all / n_all
                score += y_c - n_c * p_all
                variance += n_c * p_all * (1 - p_all) * (n_all - n_c) / (n_all - 1)
        raw_rate = clinic_stats[clinic]["rate"]
        expected_rate = expected_y / supported_n if supported_n else float("nan")
        supported_rate = supported_y / supported_n if supported_n else float("nan")
        std[clinic] = {
            "supported_n": supported_n,
            "unsupported_n": target_n - supported_n,
            "supported_rate": supported_rate,
            "peer_expected_rate": expected_rate,
            "difference_pp": 100 * (supported_rate - expected_rate) if supported_n else float("nan"),
        }
        observed_z[clinic] = score / np.sqrt(variance) if variance > 0 else 0.0
        variances[clinic] = variance

    # Conditional permutation: within each case-mix stratum, shuffle the
    # observed no-show labels across clinics while keeping clinic sample sizes
    # fixed. The max-statistic reference adjusts for scanning all clinics.
    rng = np.random.default_rng(args.seed)
    sim_scores = np.zeros((args.permutations, len(clinics)), dtype=float)
    clinic_index = {clinic: i for i, clinic in enumerate(clinics)}
    for stratum, entries in strata.items():
        n_by_clinic = Counter(clinic for clinic, _ in entries)
        y_total = sum(y for _, y in entries)
        n_total = len(entries)
        p_total = y_total / n_total
        present = sorted(n_by_clinic)
        remaining_n = n_total
        remaining_y = np.full(args.permutations, y_total, dtype=int)
        randomized = np.zeros((args.permutations, len(present)), dtype=int)
        for j, clinic in enumerate(present[:-1]):
            n_c = n_by_clinic[clinic]
            draws = rng.hypergeometric(
                remaining_y,
                remaining_n - remaining_y,
                n_c,
            )
            randomized[:, j] = draws
            remaining_y -= draws
            remaining_n -= n_c
        randomized[:, -1] = remaining_y
        for j, clinic in enumerate(present):
            n_c = n_by_clinic[clinic]
            sim_scores[:, clinic_index[clinic]] += randomized[:, j] - n_c * p_total

    z_values = np.array([observed_z[c] for c in clinics])
    z_sd = np.array([np.sqrt(variances[c]) for c in clinics])
    sim_z = np.divide(sim_scores, z_sd, out=np.zeros_like(sim_scores), where=z_sd > 0)
    max_sim_z = sim_z.max(axis=1)
    p_raw = {
        clinic: (1 + int(np.sum(sim_z[:, clinic_index[clinic]] >= observed_z[clinic])))
        / (args.permutations + 1)
        for clinic in clinics
    }
    p_adjusted = {
        clinic: (1 + int(np.sum(max_sim_z >= observed_z[clinic])))
        / (args.permutations + 1)
        for clinic in clinics
    }

    # Output clinic rate table with both the observed rate and the fair,
    # case-mix-standardized comparison to same-stratum peers.
    output = []
    for clinic in clinics:
        s = clinic_stats[clinic]
        m = std[clinic]
        meta = clinic_catalogue.get(clinic, {})
        output.append({
            "clinic_id": clinic,
            "city": meta.get("city", ""),
            "opened_on": meta.get("opened_on", ""),
            "eligible_known_outcome_bookings": s["eligible"],
            "no_show_bookings": s["no_show"],
            "collected_bookings": s["collected"],
            "missing_or_unrecognized_outcome_bookings": s["unknown"],
            "no_show_rate_pct": round(100 * s["rate"], 3),
            "wilson_95_low_pct": round(s["ci_low"], 3),
            "wilson_95_high_pct": round(s["ci_high"], 3),
            "missing_outcome_pct_of_roster": round(100 * s["missing_rate"], 3),
            "no_show_if_missing_not_no_show_pct": round(100 * s["lower_sensitivity"], 3),
            "no_show_if_all_missing_are_no_shows_pct": round(100 * s["upper_sensitivity"], 3),
            "case_mix_supported_bookings": m["supported_n"],
            "case_mix_unsupported_bookings": m["unsupported_n"],
            "standardized_rate_pct": round(100 * m["supported_rate"], 3),
            "same_mix_peer_expected_rate_pct": round(100 * m["peer_expected_rate"], 3),
            "standardized_difference_pp": round(m["difference_pp"], 3),
            "conditional_shuffle_z": round(observed_z[clinic], 3),
            "shuffle_p_one_sided": round(p_raw[clinic], 6),
            "shuffle_p_max_adjusted": round(p_adjusted[clinic], 6),
        })
    output.sort(key=lambda row: row["no_show_rate_pct"], reverse=True)
    write_csv(
        output_dir / "brief_d_clinic_rates.csv", output,
        list(output[0].keys()),
    )

    # Show the risk composition for the observed top raw-rate clinic and for
    # the top max-statistic clinic, by channel, test count, time and weekday.
    top_raw = max(clinics, key=lambda c: clinic_stats[c]["rate"])
    top_adjusted = max(clinics, key=lambda c: observed_z[c])
    factors = []
    for bid, a in cohort.items():
        for factor, value in (
            ("channel", a["channel"]),
            ("test_count", test_band(a["test_count"])),
            ("slot_time", time_band(a["slot_at"])),
            ("weekday_type", a["stratum"][4]),
            ("appointment_month", a["year_month"]),
        ):
            factors.append((a["clinic_id"], factor, value, a["outcome"] == "no_show"))
    factor_counts = defaultdict(Counter)
    for clinic, factor, value, no_show in factors:
        key = (clinic, factor, value)
        factor_counts[key]["eligible"] += 1
        factor_counts[key]["no_show"] += int(no_show)
    factor_output = []
    focus_clinics = {top_raw, top_adjusted}
    for (clinic, factor, value), counter in sorted(factor_counts.items()):
        if clinic not in focus_clinics:
            continue
        factor_output.append({
            "clinic_id": clinic,
            "factor": factor,
            "category": value,
            "eligible_bookings": counter["eligible"],
            "no_show_bookings": counter["no_show"],
            "no_show_rate_pct": round(counter["no_show"] / counter["eligible"] * 100, 3),
        })
    write_csv(
        output_dir / "brief_d_case_mix.csv", factor_output,
        ["clinic_id", "factor", "category", "eligible_bookings", "no_show_bookings", "no_show_rate_pct"],
    )

    # Month-level trend for all clinics, allowing a separate check of the
    # March/April system migration for Chennai and Jaipur.
    monthly = defaultdict(Counter)
    for a in appointments.values():
        key = (a["clinic_id"], a["year_month"], a["source_system"] or "unknown")
        if a["outcome"] in outcomes:
            monthly[key]["eligible"] += 1
            monthly[key]["no_show"] += int(a["outcome"] == "no_show")
            monthly[key]["collected"] += int(a["outcome"] == "collected")
        else:
            monthly[key]["unknown"] += 1
    monthly_output = []
    for (clinic, month, system), counter in sorted(monthly.items()):
        monthly_output.append({
            "clinic_id": clinic,
            "city": clinic_catalogue.get(clinic, {}).get("city", ""),
            "month": month,
            "source_system": system,
            "eligible_known_outcome_bookings": counter["eligible"],
            "no_show_bookings": counter["no_show"],
            "collected_bookings": counter["collected"],
            "missing_or_unrecognized_outcome_bookings": counter["unknown"],
            "no_show_rate_pct": round(counter["no_show"] / counter["eligible"] * 100, 3),
        })
    write_csv(
        output_dir / "brief_d_monthly_clinic_rates.csv", monthly_output,
        ["clinic_id", "city", "month", "source_system", "eligible_known_outcome_bookings", "no_show_bookings", "collected_bookings", "missing_or_unrecognized_outcome_bookings", "no_show_rate_pct"],
    )

    # Chance-reference audit row: the largest raw-rate clinic and the largest
    # case-mix-conditional z-score clinic may differ because sample sizes do.
    chance_output = []
    for label, clinic in (("highest_raw_rate", top_raw), ("largest_conditional_z", top_adjusted)):
        s, m = clinic_stats[clinic], std[clinic]
        chance_output.append({
            "selection_rule": label,
            "clinic_id": clinic,
            "city": clinic_catalogue.get(clinic, {}).get("city", ""),
            "eligible_bookings": s["eligible"],
            "no_show_bookings": s["no_show"],
            "observed_raw_rate_pct": round(100 * s["rate"], 3),
            "same_case_mix_peer_expected_rate_pct": round(100 * m["peer_expected_rate"], 3),
            "standardized_difference_pp": round(m["difference_pp"], 3),
            "conditional_shuffle_z": round(observed_z[clinic], 3),
            "shuffle_p_one_sided": round(p_raw[clinic], 6),
            "shuffle_p_max_adjusted": round(p_adjusted[clinic], 6),
            "permutations": args.permutations,
            "seed": args.seed,
        })
    write_csv(
        output_dir / "brief_d_chance_reference.csv", chance_output,
        list(chance_output[0].keys()),
    )

    # A compact chart: clinic volumes on the x-axis, no-show rate on y, and
    # Wilson intervals to make the small-sample clinics visibly uncertain.
    try:
        os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "brief_d_matplotlib"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ordered = sorted(clinics, key=lambda c: clinic_stats[c]["eligible"])
        x = np.array([clinic_stats[c]["eligible"] for c in ordered])
        y = np.array([100 * clinic_stats[c]["rate"] for c in ordered])
        lower = np.array([clinic_stats[c]["ci_low"] for c in ordered])
        upper = np.array([clinic_stats[c]["ci_high"] for c in ordered])
        fig, ax = plt.subplots(figsize=(11, 6.5))
        ax.errorbar(x, y, yerr=np.vstack((y - lower, upper - y)), fmt="o", alpha=0.75, capsize=2)
        for clinic in {top_raw, top_adjusted}:
            i = ordered.index(clinic)
            ax.annotate(clinic, (x[i], y[i]), xytext=(6, 5), textcoords="offset points", fontsize=8)
        ax.axhline(100 * sum(s["no_show"] for s in clinic_stats.values()) / sum(s["eligible"] for s in clinic_stats.values()), color="gray", linestyle="--", linewidth=1, label="overall rate")
        ax.set_xscale("log")
        ax.set_xlabel("Eligible bookings with known outcome (log scale)")
        ax.set_ylabel("No-show rate (%) with 95% Wilson interval")
        ax.set_title("Clinic no-show rate and sample size — H1 2026")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(output_dir / "brief_d_clinic_rates.png", dpi=160)
        plt.close(fig)
    except ImportError:
        print("matplotlib unavailable; skipped PNG chart (CSV outputs still written).")

    known_total = sum(s["eligible"] for s in clinic_stats.values())
    no_show_total = sum(s["no_show"] for s in clinic_stats.values())
    unknown_total = sum(s["unknown"] for s in clinic_stats.values())
    overall_rate = 100 * no_show_total / known_total
    print("Brief D — One Clinic, H1 2026 slot dates")
    print(f"Eligible bookings with known outcome: {known_total:,}; no-shows: {no_show_total:,}; rate: {overall_rate:.2f}%")
    print(f"Eligible bookings with missing or unrecognized collection outcome: {unknown_total:,} (reported separately, not labelled no-show)")
    print(f"Highest raw rate: {top_raw} ({clinic_stats[top_raw]['no_show']}/{clinic_stats[top_raw]['eligible']}, {100*clinic_stats[top_raw]['rate']:.2f}%)")
    print(f"Largest case-mix-conditional z: {top_adjusted} ({observed_z[top_adjusted]:.2f}; max-statistic adjusted p={p_adjusted[top_adjusted]:.4f})")
    print(f"Wrote clinic rates, case mix, monthly rates, permutation reference and chart to {output_dir}")


if __name__ == "__main__":
    main()
