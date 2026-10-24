"""Clean the invoice, gateway and settlement exports for the finance analysis."""

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
TABLES = {
    "invoices": {
        "pattern": "invoices/invoices_*.csv.gz", "file": "invoices.csv", "key": "invoice_id",
        "columns": "invoice_id invoice_date booking_id city channel amount_rs source_file source_row",
        "money": [("amount", "amount_rs", False)],
    },
    "gateway_payments": {
        "pattern": "payments/gateway_export_*.csv.gz", "file": "gateway_payments.csv", "key": "payment_id",
        "columns": "payment_id invoice_ref_raw invoice_ref amount_rs status created_at_epoch created_at_utc created_at_ist method settlement_id source_file source_row",
        "money": [("amount_paise", "amount_rs", True)],
    },
    "settlements": {
        "pattern": "payments/settlements_*.csv.gz", "file": "settlements.csv", "key": "settlement_id",
        "columns": "settlement_id amount_rs fees_rs tax_rs utr created_at_epoch created_at_utc created_at_ist status source_file source_row",
        "money": [("amount_paise", "amount_rs", True), ("fees_paise", "fees_rs", True), ("tax_paise", "tax_rs", True)],
    },
}


def read_rows(path):
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream)
        for number, row in enumerate(reader, 2):
            row = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
            if reader.fieldnames and all(row.get(key) == key for key in reader.fieldnames):
                yield number, None
            else:
                yield number, row


def to_money(value, paise=False):
    if not value:
        return "", "blank"
    try:
        amount = Decimal(value.replace(",", "")) / (100 if paise else 1)
        return f"{amount:.2f}", ""
    except (InvalidOperation, ValueError):
        return "", "invalid"


def to_times(value):
    try:
        stamp = datetime.fromtimestamp(int(value), timezone.utc)
        return stamp.isoformat(), stamp.astimezone(IST).isoformat(), ""
    except (ValueError, OverflowError, OSError, TypeError):
        return "", "", "invalid" if value else "blank"


def save_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="folder containing invoices/ and payments/")
    parser.add_argument("--output-dir", help="where to write the cleaned tables")
    args = parser.parse_args()

    starter = (ROOT / "data/raw").is_dir()
    source = Path(args.source_dir).resolve() if args.source_dir else ROOT / "data/raw" if starter else ROOT
    output = Path(args.output_dir).resolve() if args.output_dir else ROOT / "data/clean/brief_c" if starter else ROOT / "cleaned_brief_c"
    output.mkdir(parents=True, exist_ok=True)
    files = {name: sorted(source.glob(spec["pattern"])) for name, spec in TABLES.items()}
    if any(not paths for paths in files.values()):
        raise FileNotFoundError("Expected invoice, gateway and settlement CSV.GZ files.")

    issues, profile, accounting = [], {"scope": "Brief C finance tables", "tables": {}}, []

    def flag(table, path, number, key, field, value, issue):
        issues.append(dict(dataset=table, source_file=path.name, source_row=number,
                           record_id=key, field=field, observed_value=value, issue=issue))

    for table, spec in TABLES.items():
        rows, seen, bookings, dates, counts = [], set(), set(), [], Counter()
        total = Decimal(0)

        for path in files[table]:
            for number, row in read_rows(path):
                if row is None:
                    counts["repeated_headers"] += 1
                    continue
                counts["rows"] += 1
                row = {key: value for key, value in row.items() if key not in {"patient_id", "patient_name"}}
                key_field = spec["key"]
                key = row.get(key_field, "")
                key = key.upper() if key_field == "invoice_id" else key
                row[key_field] = key

                if not key:
                    flag(table, path, number, key, key_field, key, "blank ID retained")
                elif not re.fullmatch(ID_PATTERNS[key_field], key, re.I):
                    flag(table, path, number, key, key_field, key, "ID format needs review")
                if key in seen:
                    counts["duplicate_ids"] += 1
                    flag(table, path, number, key, key_field, key, "duplicate ID retained")
                seen.add(key)

                for raw_field, clean_field, paise in spec["money"]:
                    value, problem = to_money(row.get(raw_field), paise)
                    row[clean_field] = value
                    if problem:
                        counts[f"{problem}_{clean_field}"] += 1
                        flag(table, path, number, key, raw_field, row.get(raw_field, ""), f"{problem} amount retained blank")
                    else:
                        total += Decimal(value)

                if table == "invoices":
                    row["city"] = "Bengaluru" if row.get("city", "").lower() == "bangalore" else row.get("city", "")
                    row["channel"] = row.get("channel", "").lower()
                    invoice_date = row.get("invoice_date", "")
                    try:
                        datetime.fromisoformat(invoice_date)
                        dates.append(invoice_date)
                    except ValueError:
                        flag(table, path, number, key, "invoice_date", invoice_date, "date needs review; retained")
                    booking = row.get("booking_id", "")
                    if booking and booking in bookings:
                        counts["duplicate_bookings"] += 1
                        flag(table, path, number, key, "booking_id", booking, "multiple invoices per booking")
                    if booking:
                        bookings.add(booking)

                if table == "gateway_payments":
                    row["invoice_ref_raw"] = row.get("notes_invoice_ref", "")
                    row["invoice_ref"] = row["invoice_ref_raw"].upper()
                    if not re.fullmatch(ID_PATTERNS["invoice_id"], row["invoice_ref"]):
                        flag(table, path, number, key, "notes_invoice_ref", row["invoice_ref_raw"], "invoice reference format needs review")
                    for field in ("status", "method"):
                        row[field] = row.get(field, "").lower()
                        counts[f"{field}:{row[field] or '(blank)'}"] += 1
                elif table == "settlements":
                    row["status"] = row.get("status", "").lower()

                if table != "invoices":
                    utc, ist, problem = to_times(row.get("created_at_epoch", ""))
                    row.update(created_at_utc=utc, created_at_ist=ist)
                    if problem:
                        flag(table, path, number, key, "created_at_epoch", row.get("created_at_epoch", ""), f"{problem} timestamp; retained")
                    else:
                        dates.append(utc)

                row.update(source_file=path.name, source_row=number)
                rows.append(row)

        save_csv(output / spec["file"], spec["columns"].split(), rows)
        profile["tables"][table] = {
            "source_files": [path.name for path in files[table]], "rows": counts["rows"],
            "repeated_header_rows_removed": counts["repeated_headers"], "duplicate_id_rows": counts["duplicate_ids"],
            "date_min": min(dates, default=""), "date_max": max(dates, default=""),
            "valid_money_total_rs": f"{total:.2f}",
        }
        accounting.append({"dataset": table, "source_files": len(files[table]), "input_rows": counts["rows"],
                           "cleaned_rows": len(rows), "rejected_rows": 0,
                           "repeated_headers_removed": counts["repeated_headers"]})

    profile["rows_retained_with_issues"] = len(issues)
    profile["scope_note"] = "All source periods are retained for quarter and late-payment analysis."
    (output / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    save_csv(output / "input_clean_rejected.csv", accounting[0].keys(), accounting)
    save_csv(output / "issues.csv", ["dataset", "source_file", "source_row", "record_id", "field", "observed_value", "issue"], issues)
    issue_counts = Counter((i["dataset"], i["field"], i["issue"]) for i in issues)
    save_csv(output / "quality_issue_summary.csv", ["dataset", "field", "issue", "records_flagged"],
             [dict(zip(("dataset", "field", "issue", "records_flagged"), (*key, count)))
              for key, count in sorted(issue_counts.items())])

    decisions = [
        ("scope", "Clean invoices, gateway attempts and settlements", "These feed the money bridge."),
        ("period", "Keep all supplied periods", "Adjacent dates are needed to find late receipts."),
        ("money", "Convert paise to rupees with Decimal", "Avoid rounding errors."),
        ("references", "Uppercase and preserve raw payment references", "Do not guess invoice matches during cleaning."),
        ("attempts", "Keep failed and captured attempts", "Status determines which rows are receipts."),
        ("time", "Keep epoch and add UTC and India timestamps", "Use the H1 cutoff consistently."),
        ("privacy", "Drop patient names and IDs; retain booking ID", "Keep only fields needed for audit."),
        ("issues", "Keep and flag questionable rows", "Preserve the source trail."),
    ]
    save_csv(output / "decisions_log.csv", ["decision_id", "area", "decision", "rationale"],
             [dict(zip(("decision_id", "area", "decision", "rationale"), (f"C{i:03}", *row)))
              for i, row in enumerate(decisions, 1)])
    print(f"Saved cleaned finance tables to {output}")
    for name, table in profile["tables"].items():
        print(f"{name}: {table['rows']:,} rows, {table['duplicate_id_rows']:,} duplicate IDs")
    print(f"{len(issues):,} issue rows; 0 rejected rows")


if __name__ == "__main__":
    main()
