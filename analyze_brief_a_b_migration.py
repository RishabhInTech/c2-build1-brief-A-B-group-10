"""Connect Brief A volume trends to the Chennai/Jaipur Nova migration.

Run with the full cleaned tables:
    python analyze_brief_a_b_migration.py --data-dir ../datapack/cleaned

The repo itself intentionally does not contain the full data pack. The default
searches ./cleaned then ./data/clean; --data-dir can point elsewhere.

Measure: nonblank booking-test lines grouped by booking creation month.
Treatment cities: Chennai and Jaipur; Nova activity appears in March and is
nearly/full in April 2026.
Comparison cities: Ahmedabad, Bengaluru, Hyderabad and Pune (legacy).
This is descriptive analysis; it does not prove that migration caused change.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path


MONTHS = ("01", "02", "03", "04", "05", "06")
TREATED = {"Chennai", "Jaipur"}
CONTROLS = {"Ahmedabad", "Bengaluru", "Hyderabad", "Pune"}


def rows(data_dir, filename):
    with (data_dir / filename).open(encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def write_csv(path, records, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def pct(old, new):
    return 100 * (new / old - 1) if old else float("nan")


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
    raise FileNotFoundError(
        "Cleaned tables not found. Pass --data-dir PATH containing bookings.csv, "
        "plan_2026_h1.csv, collections.csv and results.csv."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="folder containing the cleaned CSV tables")
    parser.add_argument(
        "--output-dir", default="outputs",
        help="where compact result CSVs are written (default: ./outputs)",
    )
    args = parser.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    output_dir = Path(args.output_dir).expanduser().resolve()

    # Count coded booking-test lines and exclude superseded Nova reschedules.
    plan = {
        (r["city"], r["month"][5:7]): int(r["target"])
        for r in rows(data_dir, "plan_2026_h1.csv")
    }
    volume = Counter()
    raw_volume = Counter()
    rescheduled_volume = Counter()
    channel_volume = Counter()
    source_volume = Counter()
    system_volume = Counter()
    for r in rows(data_dir, "bookings.csv"):
        created = r["created_at"]
        year, month = created[:4], created[5:7]
        if year not in ("2025", "2026") or month not in MONTHS or not (r["test_code"] or "").strip():
            continue
        city = r["city"]
        key = (year, city, month)
        raw_volume[key] += 1
        if r.get("booking_status", "").strip().lower() == "rescheduled":
            rescheduled_volume[key] += 1
            continue
        channel = r["channel"] or "(blank)"
        source = r["source"] or "(blank)"
        system = r["source_system"] or "(blank)"
        volume[key] += 1
        channel_volume[(year, city, month, channel)] += 1
        source_volume[(year, city, month, source)] += 1
        system_volume[(year, city, month, system)] += 1

    cities = sorted(TREATED | CONTROLS)
    total_2025 = sum(volume[("2025", city, month)] for city in cities for month in MONTHS)
    total_2026 = sum(volume[("2026", city, month)] for city in cities for month in MONTHS)
    raw_2026 = sum(raw_volume[("2026", city, month)] for city in cities for month in MONTHS)
    rescheduled_2026 = sum(rescheduled_volume[("2026", city, month)] for city in cities for month in MONTHS)
    total_plan = sum(plan[(city, month)] for city in cities for month in MONTHS)
    overall_output = [{
        "y2025_h1_test_lines": total_2025,
        "y2026_h1_test_lines": total_2026,
        "actual_yoy_growth_pct": round(pct(total_2025, total_2026), 2),
        "raw_2026_lines_including_rescheduled": raw_2026,
        "rescheduled_lines_excluded": rescheduled_2026,
        "raw_growth_including_rescheduled_pct": round(pct(total_2025, raw_2026), 2),
        "y2026_h1_plan": total_plan,
        "implied_plan_growth_pct": round(pct(total_2025, total_plan), 2),
        "plan_attainment_pct": round(total_2026 / total_plan * 100, 2),
        "variance_vs_plan": total_2026 - total_plan,
    }]
    write_csv(output_dir / "brief_a_h1_overall.csv", overall_output,
              ["y2025_h1_test_lines", "y2026_h1_test_lines", "actual_yoy_growth_pct",
               "raw_2026_lines_including_rescheduled", "rescheduled_lines_excluded",
               "raw_growth_including_rescheduled_pct",
               "y2026_h1_plan", "implied_plan_growth_pct", "plan_attainment_pct", "variance_vs_plan"])
    print("H1 all-city headline")
    print(f"  2025={total_2025:,} 2026={total_2026:,} growth={pct(total_2025,total_2026):+.1f}% plan={total_plan:,} implied plan growth={pct(total_2025,total_plan):+.1f}% attainment={total_2026/total_plan*100:.1f}%")
    print(f"  Raw 2026={raw_2026:,}; excluded {rescheduled_2026:,} superseded reschedule lines (raw growth {pct(total_2025,raw_2026):+.1f}%)")

    monthly_output = []
    for month in MONTHS:
        old = sum(volume[("2025", city, month)] for city in cities)
        new = sum(volume[("2026", city, month)] for city in cities)
        raw_new = sum(raw_volume[("2026", city, month)] for city in cities)
        rescheduled = sum(rescheduled_volume[("2026", city, month)] for city in cities)
        target = sum(plan[(city, month)] for city in cities)
        monthly_output.append({"month": f"2026-{month}", "y2025_test_lines": old,
                              "y2026_test_lines": new, "plan": target,
                              "raw_2026_lines_including_rescheduled": raw_new,
                              "rescheduled_lines_excluded": rescheduled,
                              "yoy_growth_pct": round(pct(old, new), 2),
                              "variance_vs_plan": new - target,
                              "plan_attainment_pct": round(new / target * 100, 2)})
    write_csv(output_dir / "brief_a_h1_monthly.csv", monthly_output,
              ["month", "y2025_test_lines", "y2026_test_lines", "raw_2026_lines_including_rescheduled",
               "rescheduled_lines_excluded", "plan", "yoy_growth_pct",
               "variance_vs_plan", "plan_attainment_pct"])

    channel_city = []
    for city in cities:
        for channel in ("clinic", "home"):
            old = sum(channel_volume[("2025", city, month, channel)] for month in MONTHS)
            new = sum(channel_volume[("2026", city, month, channel)] for month in MONTHS)
            channel_city.append({"city": city, "channel": channel, "y2025_test_lines": old,
                                 "y2026_test_lines": new, "change": new - old,
                                 "yoy_growth_pct": round(pct(old, new), 2)})
    write_csv(output_dir / "brief_a_h1_channel_by_city.csv", channel_city,
              ["city", "channel", "y2025_test_lines", "y2026_test_lines", "change", "yoy_growth_pct"])

    city_output = []
    print("H1 volume and plan attainment by city")
    for city in cities:
        y25 = sum(volume[("2025", city, m)] for m in MONTHS)
        y26 = sum(volume[("2026", city, m)] for m in MONTHS)
        raw_y26 = sum(raw_volume[("2026", city, m)] for m in MONTHS)
        rescheduled = sum(rescheduled_volume[("2026", city, m)] for m in MONTHS)
        target = sum(plan[(city, m)] for m in MONTHS)
        group = "treated" if city in TREATED else "control"
        record = {
            "city": city, "group": group,
            "y2025_h1_test_lines": y25, "y2026_h1_test_lines": y26,
            "raw_2026_lines_including_rescheduled": raw_y26,
            "rescheduled_lines_excluded": rescheduled,
            "yoy_growth_pct": round(pct(y25, y26), 2),
            "y2026_h1_plan": target,
            "plan_attainment_pct": round(y26 / target * 100, 2),
            "variance_vs_plan": y26 - target,
        }
        city_output.append(record)
        print(
            f"  {city:12} {group:7} 2025={y25:>7,} 2026={y26:>7,} "
            f"YoY={record['yoy_growth_pct']:+.1f}% plan={target:>7,} "
            f"attainment={record['plan_attainment_pct']:.1f}%"
        )
    write_csv(
        output_dir / "brief_a_b_city_summary.csv", city_output,
        ["city", "group", "y2025_h1_test_lines", "y2026_h1_test_lines",
         "raw_2026_lines_including_rescheduled", "rescheduled_lines_excluded",
         "yoy_growth_pct", "y2026_h1_plan", "plan_attainment_pct", "variance_vs_plan"],
    )

    print("\nH1 group plan attainment")
    group_plan_output = []
    for group, group_cities in (("treated", TREATED), ("control", CONTROLS)):
        actual = sum(volume[("2026", city, m)] for city in group_cities for m in MONTHS)
        target = sum(plan[(city, m)] for city in group_cities for m in MONTHS)
        group_plan_output.append({
            "group": group, "actual_test_lines": actual, "plan": target,
            "attainment_pct": round(actual / target * 100, 2), "variance_vs_plan": actual - target,
        })
        print(f"  {group:7}: actual={actual:,} plan={target:,} attainment={actual/target*100:.1f}% gap={actual-target:+,}")
    write_csv(output_dir / "brief_a_b_group_plan.csv", group_plan_output,
              ["group", "actual_test_lines", "plan", "attainment_pct", "variance_vs_plan"])

    # Compare matched January-March (pre) and April-June (post) windows.
    group_period = Counter()
    for city in cities:
        group = "treated" if city in TREATED else "control"
        for month in MONTHS:
            period = "pre" if month in ("01", "02", "03") else "post"
            for year in ("2025", "2026"):
                group_period[(group, period, year)] += volume[(year, city, month)]
    period_output = []
    growth = {}
    print("\nGroup growth: Jan-Mar vs Apr-Jun")
    for group in ("treated", "control"):
        for period in ("pre", "post"):
            old = group_period[(group, period, "2025")]
            new = group_period[(group, period, "2026")]
            growth[(group, period)] = pct(old, new)
            period_output.append({
                "group": group, "period": period,
                "y2025_test_lines": old, "y2026_test_lines": new,
                "metric": "yoy_growth_pct", "value": round(growth[(group, period)], 2),
            })
            print(f"  {group:7} {period:4}: 2025={old:>7,} 2026={new:>7,} YoY={growth[(group, period)]:+.1f}%")
    post_gap = growth[("treated", "post")] - growth[("control", "post")]
    pre_gap = growth[("treated", "pre")] - growth[("control", "pre")]
    did = post_gap - pre_gap
    period_output.extend([
        {"group": "treated_minus_control", "period": "post_growth_gap", "metric": "percentage_points", "value": round(post_gap, 2)},
        {"group": "treated_minus_control", "period": "pre_adjusted_growth_gap", "metric": "percentage_points", "value": round(did, 2)},
    ])
    print(f"  Post-period treated-minus-control growth gap: {post_gap:+.1f} percentage points")
    print(f"  Difference-in-differences (descriptive): {did:+.1f} percentage points")
    write_csv(output_dir / "brief_a_b_period_summary.csv", period_output,
              ["group", "period", "y2025_test_lines", "y2026_test_lines", "metric", "value"])

    # City-month detail includes plan, channel, and actual system mix.
    monthly_output = []
    print("\nMonthly trend for migration cities")
    for city in sorted(TREATED):
        for month in MONTHS:
            old = volume[("2025", city, month)]
            new = volume[("2026", city, month)]
            legacy = system_volume[("2026", city, month, "legacy")]
            nova = system_volume[("2026", city, month, "nova")]
            clinic = channel_volume[("2026", city, month, "clinic")]
            home = channel_volume[("2026", city, month, "home")]
            target = plan[(city, month)]
            record = {
                "city": city, "month": f"2026-{month}",
                "y2025_test_lines": old, "y2026_test_lines": new,
                "yoy_growth_pct": round(pct(old, new), 2), "plan": target,
                "variance_vs_plan": new - target, "clinic_test_lines": clinic,
                "home_test_lines": home, "legacy_test_lines": legacy,
                "nova_test_lines": nova,
                "nova_share_pct": round(nova / new * 100, 2) if new else 0,
            }
            monthly_output.append(record)
            print(f"  {city:8} {month}: 2025={old:>6,} 2026={new:>6,} YoY={record['yoy_growth_pct']:+.1f}% plan gap={new-target:+,} Nova share={record['nova_share_pct']:.2f}%")
    write_csv(output_dir / "brief_a_b_monthly_treated.csv", monthly_output,
              ["city", "month", "y2025_test_lines", "y2026_test_lines", "yoy_growth_pct", "plan", "variance_vs_plan", "clinic_test_lines", "home_test_lines", "legacy_test_lines", "nova_test_lines", "nova_share_pct"])

    # H1 channel and booking-source shifts among the two treated cities.
    channel_output = []
    print("\nTreated cities, H1 channel/source shifts")
    for dimension, counter, labels in (
        ("channel", channel_volume, ("clinic", "home")),
        ("booking_source", source_volume, ("app", "phone", "walkin")),
    ):
        for label in labels:
            old = sum(counter[("2025", c, m, label)] for c in TREATED for m in MONTHS)
            new = sum(counter[("2026", c, m, label)] for c in TREATED for m in MONTHS)
            record = {"dimension": dimension, "value": label, "y2025_test_lines": old,
                      "y2026_test_lines": new, "change": new-old,
                      "yoy_growth_pct": round(pct(old, new), 2)}
            channel_output.append(record)
            print(f"  {dimension:13} {label:7}: 2025={old:>7,} 2026={new:>7,} change={new-old:>+7,} YoY={record['yoy_growth_pct']:+.1f}%")
    write_csv(output_dir / "brief_a_b_channel_summary.csv", channel_output,
              ["dimension", "value", "y2025_test_lines", "y2026_test_lines", "change", "yoy_growth_pct"])

    # Join diagnostics use two distinct grains: collection coverage per unique
    # booking ID; result coverage per booking-test line. Do not mix denominators.
    booking_meta = {}
    test_line_group = Counter()
    test_line_matches = Counter()
    for r in rows(data_dir, "bookings.csv"):
        ym = r["created_at"][:7]
        code = (r["test_code"] or "").strip()
        if (ym[:4] not in ("2025", "2026") or ym[5:7] not in MONTHS or not code
                or r.get("booking_status", "").strip().lower() == "rescheduled"):
            continue
        bid = r["booking_id"]
        group = "treated" if r["city"] in TREATED else "control"
        key = (ym[:4], group, r["source_system"])
        booking_meta[bid] = key
        test_line_group[key] += 1

    collection_seen = set()
    for r in rows(data_dir, "collections.csv"):
        if r["booking_id"] in booking_meta:
            collection_seen.add(r["booking_id"])

    result_pairs = set()
    for r in rows(data_dir, "results.csv"):
        result_pairs.add((r["booking_id"], r["test_code"]))
    for r in rows(data_dir, "bookings.csv"):
        ym = r["created_at"][:7]
        code = (r["test_code"] or "").strip()
        if (ym[:4] not in ("2025", "2026") or ym[5:7] not in MONTHS or not code
                or r.get("booking_status", "").strip().lower() == "rescheduled"):
            continue
        key = booking_meta[r["booking_id"]]
        if (r["booking_id"], code) in result_pairs:
            test_line_matches[key] += 1

    booking_counts = Counter(booking_meta.values())
    collection_counts = Counter(booking_meta[bid] for bid in collection_seen)
    diagnostics = []
    print("\nCollection/result diagnostics by cohort")
    keys = sorted(set(booking_counts) | set(test_line_group))
    for key in keys:
        booking_n = booking_counts[key]
        line_n = test_line_group[key]
        collected_n = collection_counts[key]
        matched_n = test_line_matches[key]
        record = {
            "year": key[0], "group": key[1], "source_system": key[2],
            "distinct_bookings": booking_n, "bookings_with_collection": collected_n,
            "collection_booking_match_pct": round(collected_n / booking_n * 100, 2) if booking_n else 0,
            "test_lines": line_n, "test_lines_with_matching_result": matched_n,
            "result_test_line_match_pct": round(matched_n / line_n * 100, 2) if line_n else 0,
        }
        diagnostics.append(record)
        print(f"  {key[0]} {key[1]:7} {key[2]:6}: bookings with collection {collected_n:>7,}/{booking_n:>7,} ({record['collection_booking_match_pct']:.1f}%) | test lines with result {matched_n:>7,}/{line_n:>7,} ({record['result_test_line_match_pct']:.1f}%)")
    print("  Collection metric is booking-level; result metric is test-line-level; neither proves completion.")
    write_csv(output_dir / "brief_a_b_join_diagnostics.csv", diagnostics,
              ["year", "group", "source_system", "distinct_bookings", "bookings_with_collection", "collection_booking_match_pct", "test_lines", "test_lines_with_matching_result", "result_test_line_match_pct"])

    print(f"\nWrote summary CSVs to {output_dir}")
    print("Interpretation: a short post-period and only two migrated cities support hypotheses, not a causal claim.")


if __name__ == "__main__":
    main()
