"""Compare active H1 booking-test lines with the six-city plan."""

import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="cleaned", help="folder with bookings.csv and plan_2026_h1.csv")
    parser.add_argument("--output-dir", default="outputs", help="where to write summary CSVs")
    args = parser.parse_args()

    data, output = Path(args.data_dir), Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    bookings = pd.read_csv(data / "bookings.csv", usecols=[
        "created_at", "city", "channel", "test_code", "booking_status"
    ], dtype="string", low_memory=False)
    plan = pd.read_csv(data / "plan_2026_h1.csv")

    bookings["year"] = bookings["created_at"].str[:4]
    bookings["month"] = bookings["created_at"].str[5:7]
    coded = bookings["test_code"].fillna("").str.strip().ne("")
    h1 = bookings[coded & bookings["year"].isin(["2025", "2026"])
                  & bookings["month"].isin([f"{m:02}" for m in range(1, 7)])].copy()
    h1["rescheduled"] = h1["booking_status"].fillna("").str.lower().eq("rescheduled")
    active = h1[~h1["rescheduled"]]
    cities = sorted(plan["city"].unique())
    targets = plan.assign(month=plan["month"].str[-2:]).groupby(["city", "month"])["target"].sum()

    def counts(frame, keys):
        return frame.groupby(keys, observed=True).size()

    by_city = counts(active, ["city", "year"]).unstack("year", fill_value=0)
    raw_2026 = counts(h1[h1["year"] == "2026"], ["city"]).reindex(cities, fill_value=0)
    excluded = counts(h1[h1["rescheduled"] & (h1["year"] == "2026")], ["city"]).reindex(cities, fill_value=0)
    by_city["plan"] = {city: sum(targets.get((city, month), 0) for month in [f"{m:02}" for m in range(1, 7)])
                       for city in cities}
    by_city["raw_2026_lines"] = raw_2026
    by_city["rescheduled_excluded"] = excluded
    by_city["growth_pct"] = ((by_city["2026"] / by_city["2025"] - 1) * 100).round(2)
    by_city["attainment_pct"] = (by_city["2026"] / by_city["plan"] * 100).round(2)
    by_city["variance_vs_plan"] = by_city["2026"] - by_city["plan"]
    by_city["group"] = ["treated" if city in {"Chennai", "Jaipur"} else "control" for city in by_city.index]
    city_output = by_city.rename(columns={"2025": "y2025_h1_test_lines", "2026": "y2026_h1_test_lines",
        "raw_2026_lines": "raw_2026_lines_including_rescheduled", "rescheduled_excluded": "rescheduled_lines_excluded",
        "growth_pct": "yoy_growth_pct", "attainment_pct": "plan_attainment_pct"})
    city_output.rename_axis("city").reset_index().to_csv(output / "brief_a_b_city_summary.csv", index=False)

    monthly = counts(active, ["year", "month"]).unstack("year", fill_value=0)
    monthly["plan"] = {month: sum(targets.get((city, month), 0) for city in cities)
                        for month in [f"{m:02}" for m in range(1, 7)]}
    monthly["raw_2026_lines"] = counts(h1[h1["year"] == "2026"], ["month"]).reindex(monthly.index, fill_value=0)
    monthly["rescheduled_excluded"] = counts(h1[h1["rescheduled"] & (h1["year"] == "2026")], ["month"]).reindex(monthly.index, fill_value=0)
    monthly["growth_pct"] = ((monthly["2026"] / monthly["2025"] - 1) * 100).round(2)
    monthly["attainment_pct"] = (monthly["2026"] / monthly["plan"] * 100).round(2)
    monthly["variance_vs_plan"] = monthly["2026"] - monthly["plan"]
    monthly.index = "2026-" + monthly.index.astype(str)
    monthly = monthly.rename(columns={"2025": "y2025_test_lines", "2026": "y2026_test_lines",
        "raw_2026_lines": "raw_2026_lines_including_rescheduled", "rescheduled_excluded": "rescheduled_lines_excluded",
        "growth_pct": "yoy_growth_pct", "attainment_pct": "plan_attainment_pct"})
    monthly.rename_axis("month").reset_index().to_csv(output / "brief_a_h1_monthly.csv", index=False)

    channels = counts(active[active["channel"].isin(["clinic", "home"])],
                      ["city", "channel", "year"]).unstack("year", fill_value=0)
    channels["change"] = channels["2026"] - channels["2025"]
    channels["growth_pct"] = ((channels["2026"] / channels["2025"] - 1) * 100).round(2)
    channels.rename(columns={"2025": "y2025_test_lines", "2026": "y2026_test_lines",
                             "growth_pct": "yoy_growth_pct"}).reset_index().to_csv(
        output / "brief_a_h1_channel_by_city.csv", index=False)

    old, new, raw = int(by_city["2025"].sum()), int(by_city["2026"].sum()), int(raw_2026.sum())
    target = int(by_city["plan"].sum())
    summary = pd.DataFrame([{
        "y2025_h1_test_lines": old, "y2026_h1_test_lines": new,
        "actual_yoy_growth_pct": round((new / old - 1) * 100, 2),
        "raw_2026_lines_including_rescheduled": raw,
        "rescheduled_lines_excluded": raw - new,
        "raw_growth_including_rescheduled_pct": round((raw / old - 1) * 100, 2),
        "y2026_h1_plan": target,
        "implied_plan_growth_pct": round((target / old - 1) * 100, 2),
        "plan_attainment_pct": round(new / target * 100, 2),
        "variance_vs_plan": new - target,
    }])
    summary.to_csv(output / "brief_a_h1_overall.csv", index=False)
    row = summary.iloc[0]
    print(f"Active lines: {new:,} vs {old:,} (+{row.actual_yoy_growth_pct:.2f}%).")
    print(f"Plan: {target:,} (+{row.implied_plan_growth_pct:.2f}%); shortfall {target - new:,} lines.")
    print(f"Excluded {raw - new:,} superseded reschedule lines; unfiltered growth was {row.raw_growth_including_rescheduled_pct:.2f}%.")


if __name__ == "__main__":
    main()
