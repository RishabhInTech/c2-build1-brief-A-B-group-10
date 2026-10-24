"""Clean the finance files needed for Brief C.

Run from the project folder with ``python clean_brief_c.py``. Optional:
``python clean_brief_c.py --source-dir PATH --output-dir PATH``
"""

import argparse
import csv
import gzip
import json
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
IST = ZoneInfo("Asia/Kolkata")
ID_PATTERNS = {
    "invoice_id": r"INV-\d{4}-\d{6}",
    "payment_id": r"pay_[0-9a-f]{10}",
    "settlement_id": r"setl_[0-9a-f]{8}",
}


def source_rows(path):
    """Read a gzipped CSV, returning trimmed rows and their original line numbers."""
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        for number, row in enumerate(reader, 2):
            if header and all(row.get(col) == col for col in header):
                yield number, None  # repeated header embedded in the file
            else:
                yield number, {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}


def money(value, paise=False):
    """Format money exactly in rupees; return a short issue label if unusable."""
    if not value:
        return "", "blank"
    try:
        amount = Decimal(value.replace(",", ""))
        if paise:
            amount /= 100
        return f"{amount.quantize(Decimal('.01')):.2f}", ""
    except (InvalidOperation, ValueError):
        return "", "invalid"


def times(value):
    """Convert Unix seconds to UTC and India time, preserving the source separately."""
    try:
        point = datetime.fromtimestamp(int(value), timezone.utc)
        return point.isoformat(), point.astimezone(IST).isoformat(), ""
    except (ValueError, OverflowError, OSError, TypeError):
        return "", "", "blank" if not value else "invalid"


def save_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="folder containing invoices/ and payments/")
    parser.add_argument("--output-dir", help="where the cleaned Brief C files will be saved")
    args = parser.parse_args()

    starter = (ROOT / "data/raw").is_dir()
    source = Path(args.source_dir).resolve() if args.source_dir else ROOT / "data/raw" if starter else ROOT
    output = Path(args.output_dir).resolve() if args.output_dir else ROOT / "data/clean/brief_c" if starter else ROOT / "cleaned_brief_c"
    files = {
        "invoices": sorted((source / "invoices").glob("invoices_*.csv.gz")),
        "gateway_payments": sorted((source / "payments").glob("gateway_export_*.csv.gz")),
        "settlements": sorted((source / "payments").glob("settlements_*.csv.gz")),
    }
    if any(not group for group in files.values()):
        raise FileNotFoundError("Need invoice, gateway export, and settlement CSV.GZ files.")
    output.mkdir(parents=True, exist_ok=True)

    # Each spec describes input columns, output columns, and money fields.
    specs = {
        "invoices": ("invoices.csv", ["invoice_id", "invoice_date", "booking_id", "city", "channel", "amount_rs", "source_file", "source_row"], [("amount", "amount_rs", False)]),
        "gateway_payments": ("gateway_payments.csv", ["payment_id", "invoice_ref_raw", "invoice_ref", "amount_rs", "status", "created_at_epoch", "created_at_utc", "created_at_ist", "method", "settlement_id", "source_file", "source_row"], [("amount_paise", "amount_rs", True)]),
        "settlements": ("settlements.csv", ["settlement_id", "amount_rs", "fees_rs", "tax_rs", "utr", "created_at_epoch", "created_at_utc", "created_at_ist", "status", "source_file", "source_row"], [("amount_paise", "amount_rs", True), ("fees_paise", "fees_rs", True), ("tax_paise", "tax_rs", True)]),
    }
    issues, profile, accounting = [], {"scope": "Brief C financial tables only", "tables": {}}, []

    def flag(table, file, row, key, field, value, message):
        issues.append(dict(dataset=table, source_file=file.name, source_row=row,
                           record_id=key, field=field, observed_value=value, issue=message))

    for table, group in files.items():
        filename, columns, money_fields = specs[table]
        output_rows, seen, dates, counts = [], set(), [], Counter()
        bookings = set()
        total = Decimal(0)
        for file in group:
            for number, raw in source_rows(file):
                if raw is None:
                    counts["repeated_headers"] += 1
                    continue
                counts["rows"] += 1
                row = {k: v for k, v in raw.items() if k not in {"patient_id", "patient_name"}}
                key_field = {"invoices": "invoice_id", "gateway_payments": "payment_id", "settlements": "settlement_id"}[table]
                key = row.get(key_field, "")
                if key_field == "invoice_id":
                    key = key.upper()
                row[key_field] = key

                if not key:
                    flag(table, file, number, key, key_field, "", "blank ID retained")
                elif key_field in ID_PATTERNS and not re.fullmatch(ID_PATTERNS[key_field], key, re.I):
                    flag(table, file, number, key, key_field, key, "ID format needs review")
                if key in seen:
                    counts["duplicate_ids"] += 1
                    flag(table, file, number, key, key_field, key, "duplicate ID retained")
                seen.add(key)

                for raw_field, clean_field, paise in money_fields:
                    amount, problem = money(row.get(raw_field), paise)
                    row[clean_field] = amount
                    if problem:
                        counts[f"{problem}_{clean_field}"] += 1
                        flag(table, file, number, key, raw_field, row.get(raw_field, ""), f"{problem} amount retained as blank")
                    else:
                        total += Decimal(amount)

                if table == "invoices":
                    row["city"] = "Bengaluru" if row.get("city", "").lower() == "bangalore" else row.get("city", "")
                    row["channel"] = row.get("channel", "").lower()
                    date = row.get("invoice_date", "")
                    try:
                        datetime.fromisoformat(date)
                        dates.append(date)
                    except ValueError:
                        flag(table, file, number, key, "invoice_date", date, "date needs review; retained")
                    booking = row.get("booking_id", "")
                    if booking and booking in bookings:
                        counts["duplicate_bookings"] += 1
                        flag(table, file, number, key, "booking_id", booking, "multiple invoices for booking; retained")
                    if booking:
                        bookings.add(booking)

                if table == "gateway_payments":
                    row["invoice_ref_raw"] = row.get("notes_invoice_ref", "")
                    row["invoice_ref"] = row["invoice_ref_raw"].upper()
                    if not row["invoice_ref"] or not re.fullmatch(ID_PATTERNS["invoice_id"], row["invoice_ref"]):
                        flag(table, file, number, key, "notes_invoice_ref", row["invoice_ref_raw"],
                             "blank or unexpected invoice reference; value retained for review")
                    row["status"] = row.get("status", "").lower()
                    row["method"] = row.get("method", "").lower()
                    for name in ("status", "method"):
                        counts[name + ":" + (row.get(name) or "(blank)")] += 1

                if table == "settlements":
                    row["status"] = row.get("status", "").lower()

                if table != "invoices":
                    epoch = row.get("created_at_epoch", "")
                    utc, ist, problem = times(epoch)
                    row.update(created_at_utc=utc, created_at_ist=ist)
                    if problem:
                        flag(table, file, number, key, "created_at_epoch", epoch, f"{problem} timestamp; retained")
                    elif utc:
                        dates.append(utc)
                row.update(source_file=file.name, source_row=number)
                output_rows.append(row)

        save_csv(output / filename, columns, output_rows)
        profile["tables"][table] = {"source_files": [p.name for p in group], "rows": counts["rows"],
            "repeated_header_rows_removed": counts["repeated_headers"], "duplicate_id_rows": counts["duplicate_ids"],
            "date_min": min(dates, default=""), "date_max": max(dates, default=""),
            "valid_money_total_rs": f"{total:.2f}"}
        accounting.append({"dataset": table, "source_files": len(group), "input_rows": counts["rows"],
            "cleaned_rows": len(output_rows), "rejected_rows": 0, "repeated_headers_removed": counts["repeated_headers"]})

    profile["rows_retained_with_issues"] = len(issues)
    profile["scope_note"] = "All supplied finance periods are kept; choose and document the target quarter during analysis."
    (output / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    save_csv(output / "input_clean_rejected.csv", list(accounting[0]), accounting)
    save_csv(output / "issues.csv", ["dataset", "source_file", "source_row", "record_id", "field", "observed_value", "issue"], issues)
    summary = Counter((i["dataset"], i["field"], i["issue"]) for i in issues)
    save_csv(output / "quality_issue_summary.csv", ["dataset", "field", "issue", "records_flagged"],
             [dict(zip(("dataset", "field", "issue", "records_flagged"), (*k, n))) for k, n in sorted(summary.items())])

    decisions = [
        ("scope", "Clean invoices, gateway payments, and settlements", "These are Brief C's finance records."),
        ("period", "Keep every supplied period", "Quarter and late-payment timing need analysis."),
        ("money", "Convert paise to rupees with Decimal", "Avoid floating point rounding."),
        ("references", "Trim and uppercase payment invoice references; preserve raw value", "Do not guess fuzzy invoice matches."),
        ("attempts", "Keep failed and captured payment attempts", "Analysis must avoid double-counting attempts."),
        ("time", "Keep epoch and add UTC and India timestamps", "Use consistent local quarter assignment."),
        ("privacy", "Drop patient name and ID; retain booking ID", "Booking ID supports invoice-per-visit checks."),
        ("retention", "Keep rows with issues and log them", "Preserve an auditable financial bridge."),
    ]
    save_csv(output / "decisions_log.csv", ["decision_id", "area", "decision", "rationale"],
             [dict(zip(("decision_id", "area", "decision", "rationale"), (f"C{i:03}", *d))) for i, d in enumerate(decisions, 1)])
    print(f"Brief C clean files saved to: {output}")
    for name, info in profile["tables"].items():
        print(f"{name}: {info['rows']:,} rows; {info['repeated_header_rows_removed']:,} repeated headers")
    print(f"Issues logged: {len(issues):,}; rows rejected: 0")


if __name__ == "__main__":
    main()
