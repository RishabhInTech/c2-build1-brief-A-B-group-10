"""Explore Brief A test-volume growth, with a Jaipur drill-down.

Run from the project root:
    python analyze_brief_a_jaipur.py --data-dir PATH_TO_CLEANED

The primary metric is one nonblank booking test line, grouped by booking
created_at month. Plan is compared only for 2026 H1. Results/collections are
separate operational signals, not substitutes for the plan metric.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path


MONTHS = ("01", "02", "03", "04", "05", "06")
YEARS = ("2025", "2026")


def read_rows(data_dir, filename):
    with (data_dir / filename).open(newline="", encoding="utf-8") as file:
        yield from csv.DictReader(file)


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
        "Cleaned tables not found. Pass --data-dir PATH containing bookings.csv "
        "and plan_2026_h1.csv."
    )


def pct_change(old, new):
    return (new / old - 1) * 100 if old else float("nan")


def fmt_pct(value):
    return f"{value:+.1f}%"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="folder containing the cleaned CSV tables")
    args = parser.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    # Step 1: build the 2026 plan lookup: city + month -> target.
    plan = {
        (row["city"], row["month"][5:7]): int(row["target"])
        for row in read_rows(data_dir, "plan_2026_h1.csv")
    }

    # Step 2: count test lines from bookings, retaining useful dimensions.
    city_month = Counter()
    channel = Counter()
    monthly_channel = Counter()
    city_channel = Counter()
    clinic = Counter()
    clinic_channel = Counter()
    source = Counter()
    source_system = Counter()
    test = Counter()

    for row in read_rows(data_dir, "bookings.csv"):
        month = row["created_at"][:7]
        year, month_num = month[:4], month[5:7]
        code = row["test_code"].strip()

        # Exclude out-of-period rows and blank/unknown test lines from volume.
        if year not in YEARS or month_num not in MONTHS or not code:
            continue

        city = row["city"]
        channel_name = row["channel"] or "(blank)"
        city_month[(year, city, month_num)] += 1
        channel[(year, channel_name)] += 1
        if city == "Jaipur":
            monthly_channel[(year, month_num, channel_name)] += 1
        city_channel[(year, city, channel_name)] += 1

        if city == "Jaipur":
            clinic[(year, month_num, row["clinic_id"])] += 1
            clinic_channel[(year, row["clinic_id"], channel_name)] += 1
            source[(year, channel_name, row["source"] or "(blank)")] += 1
            source_system[(year, month_num, row["source_system"] or "(blank)")] += 1
            test[(year, row["test_code"])] += 1

    # Step 3: headline, compare totals using matched Jan-Jun periods.
    old = sum(city_month[("2025", city, m)] for city, m in {(c, m) for c, m in plan})
    actual = sum(city_month[("2026", city, m)] for city, m in plan)
    target = sum(plan.values())
    print("H1 all-city test volume")
    print(f"  2025: {old:,} | 2026: {actual:,} | growth: {fmt_pct(pct_change(old, actual))}")
    print(f"  2026 plan: {target:,} | variance: {actual-target:+,} ({fmt_pct(pct_change(target, actual))} vs plan)")

    # Step 4: city cuts identify where to drill down.
    print("\nCity actual vs plan")
    cities = sorted({city for city, _ in plan})
    for city in cities:
        y25 = sum(city_month[("2025", city, m)] for m in MONTHS)
        y26 = sum(city_month[("2026", city, m)] for m in MONTHS)
        city_plan = sum(plan[(city, m)] for m in MONTHS)
        print(f"  {city:12} 2025={y25:>7,} 2026={y26:>7,} YoY={fmt_pct(pct_change(y25,y26)):>8} plan={city_plan:>7,} gap={y26-city_plan:>7,}")

    # Step 5: Jaipur by month, target, and channel.
    print("\nJaipur monthly trend (test lines)")
    for m in MONTHS:
        y25 = city_month[("2025", "Jaipur", m)]
        y26 = city_month[("2026", "Jaipur", m)]
        target_m = plan[("Jaipur", m)]
        home_26 = monthly_channel[("2026", m, "home")]
        clinic_26 = monthly_channel[("2026", m, "clinic")]
        print(
            f"  {m}: 2025={y25:>5,} 2026={y26:>5,} "
            f"YoY={fmt_pct(pct_change(y25,y26)):>8} plan={target_m:>5,} "
            f"gap={y26-target_m:>5,} | "
            f"home {home_26:,} / clinic {clinic_26:,}"
        )

    # A monthly channel counter is clearer for interpreting changes.
    print("\nJaipur channel contribution, H1")
    for name in ("clinic", "home"):
        y25 = sum(monthly_channel[("2025", m, name)] for m in MONTHS)
        y26 = sum(monthly_channel[("2026", m, name)] for m in MONTHS)
        print(f"  {name:7} 2025={y25:>6,} 2026={y26:>6,} change={y26-y25:>+6,} YoY={fmt_pct(pct_change(y25,y26))}")

    # Step 6: clinic, source and test cuts reveal what composes the movement.
    print("\nJaipur clinics, H1")
    clinic_ids = sorted({cl for _, _, cl in clinic})
    for cl in clinic_ids:
        y25 = sum(clinic[("2025", m, cl)] for m in MONTHS)
        y26 = sum(clinic[("2026", m, cl)] for m in MONTHS)
        print(f"  {cl}: 2025={y25:>6,} 2026={y26:>6,} change={y26-y25:>+6,}")

    print("\nJaipur source within channel, H1")
    for ch in ("clinic", "home"):
        for src in ("app", "phone", "walkin"):
            y25 = source[("2025", ch, src)]
            y26 = source[("2026", ch, src)]
            print(f"  {ch:7} / {src:6}: 2025={y25:>6,} 2026={y26:>6,} change={y26-y25:>+6,}")

    print("\nJaipur test codes with largest declines")
    codes = sorted({code for _, code in test})
    code_rows = sorted(
        ((test[("2025", code)], test[("2026", code)], code) for code in codes),
        key=lambda values: values[1] - values[0],
    )
    catalogue = {row["test_code"]: row["test_name"] for row in read_rows(data_dir, "tests_catalogue.csv")}
    for y25, y26, code in code_rows[:8]:
        print(f"  {code} {catalogue.get(code, 'Unknown'):28} 2025={y25:>5,} 2026={y26:>5,} change={y26-y25:>+5,}")

    # System changes line up with month boundaries; expose them for validation.
    print("\nJaipur source-system mix, 2026")
    for m in MONTHS:
        legacy_count = source_system[("2026", m, "legacy")]
        nova_count = source_system[("2026", m, "nova")]
        parts = [f"legacy={legacy_count:,}", f"nova={nova_count:,}"]
        print(f"  {m}: " + ", ".join(parts))

    # Step 7: link test lines to results by booking + test code. This shows
    # whether a booked line has a matching result row; it is not plan volume.
    result_lines = Counter()
    for row in read_rows(data_dir, "results.csv"):
        result_lines[(row["booking_id"], row["test_code"])] += 1

    booked_lines = Counter()
    for row in read_rows(data_dir, "bookings.csv"):
        month = row["created_at"][:7]
        if (
            row["city"] == "Jaipur"
            and month[:4] in YEARS
            and month[5:7] in MONTHS
            and row["test_code"].strip()
        ):
            booked_lines[(month[:4], row["channel"], row["booking_id"], row["test_code"])] += 1

    print("\nJaipur booking test lines with matching result (booking cohort; diagnostic only)")
    for year in YEARS:
        for ch in ("clinic", "home"):
            lines = [key for key in booked_lines if key[0] == year and key[1] == ch]
            matched = sum(result_lines[(booking_id, code)] > 0 for _, _, booking_id, code in lines)
            rate = matched / len(lines) * 100 if lines else float("nan")
            print(f"  {year} {ch:7}: {matched:>6,}/{len(lines):>6,} = {rate:.1f}%")


if __name__ == "__main__":
    main()
