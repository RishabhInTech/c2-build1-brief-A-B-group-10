"""Connect Brief A volume trends to the Chennai/Jaipur Nova migration.

Run from the project root:
    python analyze_brief_a_b_migration.py

Measure: nonblank booking-test lines grouped by booking creation month.
Treatment cities: Chennai and Jaipur (Nova adoption begins April 2026).
Comparison cities: Ahmedabad, Bengaluru, Hyderabad and Pune (legacy).

This is descriptive analysis. Two treated cities and a short post period do not
establish that the system migration caused volume changes.
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path


DATA = Path(__file__).resolve().parent / "cleaned"
MONTHS = ("01", "02", "03", "04", "05", "06")
TREATED = {"Chennai", "Jaipur"}
CONTROLS = {"Ahmedabad", "Bengaluru", "Hyderabad", "Pune"}


def rows(filename):
    with (DATA / filename).open(encoding="utf-8", newline="") as file:
        yield from csv.DictReader(file)


def pct(old, new):
    return 100 * (new / old - 1) if old else float("nan")


def show_pct(value):
    return f"{value:+.1f}%"


def main():
    # 1) Load the plan and count test lines. Blank codes are deliberately
    # excluded, following the cleaning decision recorded in decisions_log.csv.
    plan = {
        (r["city"], r["month"][5:7]): int(r["target"])
        for r in rows("plan_2026_h1.csv")
    }
    volume = Counter()
    channel_volume = Counter()
    source_volume = Counter()
    source_system_volume = Counter()
    for r in rows("bookings.csv"):
        created = r["created_at"]
        year, month = created[:4], created[5:7]
        code = (r["test_code"] or "").strip()
        if year not in ("2025", "2026") or month not in MONTHS or not code:
            continue
        city = r["city"]
        channel = r["channel"] or "(blank)"
        volume[(year, city, month)] += 1
        channel_volume[(year, city, month, channel)] += 1
        source_volume[(year, city, month, r["source"] or "(blank)")] += 1
        source_system_volume[(year, city, month, r["source_system"] or "(blank)")] += 1

    cities = sorted(TREATED | CONTROLS)
    print("H1 volume and plan attainment by city")
    city_yoy = {}
    for city in cities:
        y25 = sum(volume[("2025", city, m)] for m in MONTHS)
        y26 = sum(volume[("2026", city, m)] for m in MONTHS)
        target = sum(plan[(city, m)] for m in MONTHS)
        city_yoy[city] = pct(y25, y26)
        group = "Nova from Apr" if city in TREATED else "legacy control"
        print(
            f"  {city:12} {group:16} 2025={y25:>7,} 2026={y26:>7,} "
            f"YoY={show_pct(city_yoy[city]):>8} plan={target:>7,} "
            f"attainment={y26/target*100:5.1f}%"
        )

    print("\nH1 group plan attainment")
    for label, group_cities in (("treated", TREATED), ("control", CONTROLS)):
        actual = sum(volume[("2026", city, m)] for city in group_cities for m in MONTHS)
        target = sum(plan[(city, m)] for city in group_cities for m in MONTHS)
        print(f"  {label:7}: actual={actual:,} plan={target:,} attainment={actual/target*100:.1f}% gap={actual-target:+,}")

    # 2) Compare treated and control groups before and after April. Use the
    # same months in 2025 as a seasonal comparison for the April-June period.
    print("\nGroup growth: Jan-Mar vs Apr-Jun")
    group_period = Counter()
    for city in cities:
        group = "treated" if city in TREATED else "control"
        for month in MONTHS:
            period = "pre" if month in ("01", "02", "03") else "post"
            for year in ("2025", "2026"):
                group_period[(group, period, year)] += volume[(year, city, month)]
    growth = {}
    for group in ("treated", "control"):
        for period in ("pre", "post"):
            old = group_period[(group, period, "2025")]
            new = group_period[(group, period, "2026")]
            growth[(group, period)] = pct(old, new)
            print(
                f"  {group:7} {period:4}: 2025={old:>7,} 2026={new:>7,} "
                f"YoY={show_pct(growth[(group, period)])}"
            )
    post_gap_pp = growth[("treated", "post")] - growth[("control", "post")]
    pre_gap_pp = growth[("treated", "pre")] - growth[("control", "pre")]
    did_pp = post_gap_pp - pre_gap_pp
    print(
        "  Post-period treated-minus-control growth gap: "
        f"{post_gap_pp:+.1f} percentage points"
    )
    print(
        "  Difference-in-differences (post gap minus pre gap): "
        f"{did_pp:+.1f} percentage points (descriptive, not causal)"
    )

    print("\nMonthly city YoY and Nova share")
    for city in sorted(TREATED):
        print(f"  {city}")
        for month in MONTHS:
            old = volume[("2025", city, month)]
            new = volume[("2026", city, month)]
            legacy = source_system_volume[("2026", city, month, "legacy")]
            nova = source_system_volume[("2026", city, month, "nova")]
            share = 100 * nova / new if new else 0
            print(
                f"    {month}: 2025={old:>6,} 2026={new:>6,} "
                f"YoY={show_pct(pct(old,new)):>8} legacy={legacy:>6,} "
                f"nova={nova:>6,} Nova share={share:5.2f}%"
            )

    # 3) Show whether total volume movements differ by channel or source.
    print("\nTreated cities, H1 channel/source shifts")
    for dimension, counter, labels in (
        ("channel", channel_volume, ("clinic", "home")),
        ("booking source", source_volume, ("app", "phone", "walkin")),
    ):
        for label in labels:
            old = sum(counter[("2025", c, m, label)] for c in TREATED for m in MONTHS)
            new = sum(counter[("2026", c, m, label)] for c in TREATED for m in MONTHS)
            print(
                f"  {dimension:13} {label:7}: 2025={old:>7,} 2026={new:>7,} "
                f"change={new-old:>+7,} YoY={show_pct(pct(old,new))}"
            )

    # 4) Join cleaned collections and results to booking cohorts by ID. These
    # are diagnostics because collection events and results have their own
    # timestamps and unmatched rows documented in join_row_counts.csv.
    booking = {}
    for r in rows("bookings.csv"):
        ym = r["created_at"][:7]
        if ym[:4] not in ("2025", "2026") or ym[5:7] not in MONTHS or not r["test_code"].strip():
            continue
        booking[r["booking_id"]] = {
            "year": ym[:4], "month": ym[5:7], "city": r["city"],
            "group": "treated" if r["city"] in TREATED else "control",
            "channel": r["channel"], "system": r["source_system"],
            "code": r["test_code"],
        }

    collection_seen = set()
    collection_by_group = Counter()
    for r in rows("collections.csv"):
        bid = r["booking_id"]
        if bid in booking:
            b = booking[bid]
            collection_seen.add(bid)
            collection_by_group[(b["year"], b["group"], b["system"], "matched collection")] += 1
    result_pairs = set()
    for r in rows("results.csv"):
        result_pairs.add((r["booking_id"], r["test_code"]))

    print("\nCollection/result diagnostics by cohort")
    denominator = Counter()
    coll = Counter()
    result = Counter()
    for bid, b in booking.items():
        key = (b["year"], b["group"], b["system"])
        denominator[key] += 1
        coll[key] += bid in collection_seen
        result[key] += (bid, b["code"]) in result_pairs
    for key in sorted(denominator):
        n = denominator[key]
        print(
            f"  {key[0]} {key[1]:7} {key[2]:6}: lines={n:>7,} "
            f"with collection={coll[key]/n*100:5.1f}% "
            f"with matching result={result[key]/n*100:5.1f}%"
        )
    print("  These are join indicators, not final completion rates.")

    # 5) A compact verdict to connect the briefs.
    print("\nInterpretation prompts")
    print(
        "  If treated-city volume changes differ from the control cities only "
        "after April, migration-related causes merit investigation."
    )
    print(
        "  If the gap also appears in joined collections/results, the signal "
        "is less likely to be only booking capture; verify timestamp and join coverage."
    )
    print(
        "  With two treated cities and three post-migration months, these data "
        "support hypotheses, not a causal claim."
    )


if __name__ == "__main__":
    main()
