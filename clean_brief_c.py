"""Create a finance-only cleaned data pack for Kalpa Health Brief C.

Reads the invoice, gateway-payment, and settlement source exports and writes
them to cleaned_brief_c/ without changing the original data or cleaned/.
No source rows are dropped for missing IDs, malformed money values, or
duplicate identifiers; exceptions are retained and recorded in issues.csv.

Run from the project root or data-pack root:
    python clean_brief_c.py
    python clean_brief_c.py --source-dir PATH --output-dir PATH
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
INVOICE_ID_RE = re.compile(r"INV-\d{4}-\d{6}")
PAYMENT_ID_RE = re.compile(r"pay_[0-9a-f]{10}", re.IGNORECASE)
SETTLEMENT_ID_RE = re.compile(r"setl_[0-9a-f]{8}", re.IGNORECASE)


def read_source(path):
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        for source_row, row in enumerate(reader, start=2):
            # Some exports repeat their header line within the data.
            if header and all((row.get(k) or "") == k for k in header):
                yield source_row, None
            else:
                yield source_row, {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def money(value, unit):
    """Return an exact two-decimal INR string, or blank for missing/invalid."""
    if value is None or not str(value).strip():
        return "", "blank"
    raw = str(value).strip().replace(",", "")
    try:
        amount = Decimal(raw)
        if unit == "paise":
            amount /= Decimal(100)
        return f"{amount.quantize(Decimal('0.01')):.2f}", ""
    except (InvalidOperation, ValueError):
        return "", "invalid"


def epoch_times(value):
    value = (value or "").strip()
    if not value:
        return "", "", "blank"
    try:
        point = datetime.fromtimestamp(int(value), tz=timezone.utc)
        return point.isoformat(), point.astimezone(IST).isoformat(), ""
    except (ValueError, OverflowError, OSError):
        return "", "", "invalid"


def write_csv(path, columns, records):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def normalized_city(value):
    value = (value or "").strip()
    return "Bengaluru" if value.lower() == "bangalore" else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="root containing invoices/ and payments/; defaults to data/raw when present")
    parser.add_argument("--output-dir", help="separate Brief C output folder; defaults to data/clean/brief_c in the starter kit")
    args = parser.parse_args()
    if args.source_dir:
        source = Path(args.source_dir).expanduser().resolve()
    elif (ROOT / "data" / "raw" / "invoices").is_dir():
        source = ROOT / "data" / "raw"
    else:
        source = ROOT
    if args.output_dir:
        output = Path(args.output_dir).expanduser().resolve()
    elif (ROOT / "data" / "raw").is_dir():
        output = ROOT / "data" / "clean" / "brief_c"
    else:
        output = ROOT / "cleaned_brief_c"
    invoice_files = sorted((source / "invoices").glob("invoices_*.csv.gz"))
    gateway_files = sorted((source / "payments").glob("gateway_export_*.csv.gz"))
    settlement_files = sorted((source / "payments").glob("settlements_*.csv.gz"))
    if not invoice_files or not gateway_files or not settlement_files:
        raise FileNotFoundError("Expected invoice, gateway export, and settlement CSV.GZ source files.")

    output.mkdir(parents=True, exist_ok=True)
    issue_path = output / "issues.csv"
    issues = []
    profile = {"scope": "Brief C financial tables only", "tables": {}}
    accounting = []

    def flag(dataset, file, row, record_id, field, observed, reason):
        issues.append({
            "dataset": dataset, "source_file": file.name, "source_row": row,
            "record_id": record_id or "", "field": field,
            "observed_value": observed or "", "issue": reason,
        })

    # One invoice per visit is a handbook expectation. Keep booking_id to let
    # the later analysis validate that expectation; omit patient identifiers.
    invoice_cols = ["invoice_id", "invoice_date", "booking_id", "city", "channel", "amount_rs", "source_file", "source_row"]
    invoice_path = output / "invoices.csv"
    invoice_summary = {"rows": 0, "repeated_header_rows_removed": 0, "amount_total_rs": Decimal(0),
                       "blank_amount_rows": 0, "invalid_amount_rows": 0}
    invoice_ids, invoice_bookings = set(), set()
    invoice_id_duplicates = invoice_booking_duplicates = 0
    invoice_date_min = invoice_date_max = ""
    with invoice_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=invoice_cols)
        writer.writeheader()
        for file in invoice_files:
            for row_no, r in read_source(file):
                if r is None:
                    invoice_summary["repeated_header_rows_removed"] += 1
                    continue
                invoice_summary["rows"] += 1
                invoice_id = (r.get("invoice_id") or "").strip().upper()
                booking_id = (r.get("booking_id") or "").strip()
                invoice_date = (r.get("invoice_date") or "").strip()
                amount_rs, amount_issue = money(r.get("amount"), "rupees")
                city = normalized_city(r.get("city"))
                channel = (r.get("channel") or "").strip().lower()
                if not invoice_id:
                    flag("invoices", file, row_no, invoice_id, "invoice_id", "", "blank invoice ID retained")
                elif not INVOICE_ID_RE.fullmatch(invoice_id):
                    flag("invoices", file, row_no, invoice_id, "invoice_id", invoice_id, "invoice ID format needs review")
                if invoice_id in invoice_ids:
                    invoice_id_duplicates += 1
                    flag("invoices", file, row_no, invoice_id, "invoice_id", invoice_id, "duplicate invoice ID retained")
                invoice_ids.add(invoice_id)
                if not booking_id:
                    flag("invoices", file, row_no, invoice_id, "booking_id", "", "blank booking ID retained")
                elif booking_id in invoice_bookings:
                    invoice_booking_duplicates += 1
                    flag("invoices", file, row_no, invoice_id, "booking_id", booking_id, "more than one invoice for booking; retained for review")
                invoice_bookings.add(booking_id)
                if invoice_date:
                    try:
                        datetime.fromisoformat(invoice_date)
                        invoice_date_min = min(invoice_date_min, invoice_date) if invoice_date_min else invoice_date
                        invoice_date_max = max(invoice_date_max, invoice_date) if invoice_date_max else invoice_date
                    except ValueError:
                        flag("invoices", file, row_no, invoice_id, "invoice_date", invoice_date, "unparseable invoice date retained")
                else:
                    flag("invoices", file, row_no, invoice_id, "invoice_date", "", "blank invoice date retained")
                if amount_issue:
                    invoice_summary[f"{amount_issue}_amount_rows"] += 1
                    flag("invoices", file, row_no, invoice_id, "amount", r.get("amount"), f"{amount_issue} amount retained as blank")
                else:
                    invoice_summary["amount_total_rs"] += Decimal(amount_rs)
                writer.writerow({"invoice_id": invoice_id, "invoice_date": invoice_date, "booking_id": booking_id,
                                 "city": city, "channel": channel, "amount_rs": amount_rs,
                                 "source_file": file.name, "source_row": row_no})
    profile["tables"]["invoices"] = {
        "source_files": [p.name for p in invoice_files], "rows": invoice_summary["rows"],
        "repeated_header_rows_removed": invoice_summary["repeated_header_rows_removed"],
        "primary_key": "invoice_id", "duplicate_invoice_id_rows": invoice_id_duplicates,
        "duplicate_booking_id_rows": invoice_booking_duplicates,
        "invoice_date_min": invoice_date_min, "invoice_date_max": invoice_date_max,
        "amount_total_rs_over_nonblank_valid_rows": f"{invoice_summary['amount_total_rs']:.2f}",
        "blank_amount_rows": invoice_summary["blank_amount_rows"],
        "invalid_amount_rows": invoice_summary["invalid_amount_rows"],
    }
    accounting.append({"dataset": "invoices", "source_files": len(invoice_files), "input_rows_excluding_repeated_headers": invoice_summary["rows"],
                       "cleaned_rows": invoice_summary["rows"], "rejected_rows": 0,
                       "repeated_header_rows_removed": invoice_summary["repeated_header_rows_removed"],
                       "unit": "invoice rows", "decision": "Retain all source invoices; trim and normalize fields; rupee amount kept exact to paise."})

    gateway_cols = ["payment_id", "invoice_ref_raw", "invoice_ref", "amount_rs", "status", "created_at_epoch", "created_at_utc", "created_at_ist", "method", "settlement_id", "source_file", "source_row"]
    gateway_path = output / "gateway_payments.csv"
    gateway_summary = {"rows": 0, "repeated_header_rows_removed": 0, "amount_total_rs": Decimal(0),
                       "blank_amount_rows": 0, "invalid_amount_rows": 0, "blank_timestamp_rows": 0, "invalid_timestamp_rows": 0}
    payment_ids = set()
    payment_id_duplicates = 0
    gateway_statuses, gateway_methods = Counter(), Counter()
    gateway_date_min = gateway_date_max = ""
    with gateway_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=gateway_cols)
        writer.writeheader()
        for file in gateway_files:
            for row_no, r in read_source(file):
                if r is None:
                    gateway_summary["repeated_header_rows_removed"] += 1
                    continue
                gateway_summary["rows"] += 1
                payment_id = (r.get("payment_id") or "").strip()
                ref_raw = (r.get("notes_invoice_ref") or "").strip()
                invoice_ref = ref_raw.upper()
                settlement_id = (r.get("settlement_id") or "").strip()
                status = (r.get("status") or "").strip().lower()
                method = (r.get("method") or "").strip().lower()
                amount_rs, amount_issue = money(r.get("amount_paise"), "paise")
                utc, ist, time_issue = epoch_times(r.get("created_at_epoch"))
                if not payment_id:
                    flag("gateway_payments", file, row_no, payment_id, "payment_id", "", "blank payment ID retained")
                elif not PAYMENT_ID_RE.fullmatch(payment_id):
                    flag("gateway_payments", file, row_no, payment_id, "payment_id", payment_id, "payment ID format needs review")
                if payment_id in payment_ids:
                    payment_id_duplicates += 1
                    flag("gateway_payments", file, row_no, payment_id, "payment_id", payment_id, "duplicate payment ID retained")
                payment_ids.add(payment_id)
                if ref_raw and not INVOICE_ID_RE.fullmatch(invoice_ref):
                    flag("gateway_payments", file, row_no, payment_id, "notes_invoice_ref", ref_raw, "invoice reference format needs review; normalized value retained")
                if not ref_raw:
                    flag("gateway_payments", file, row_no, payment_id, "notes_invoice_ref", "", "blank invoice reference retained")
                if amount_issue:
                    gateway_summary[f"{amount_issue}_amount_rows"] += 1
                    flag("gateway_payments", file, row_no, payment_id, "amount_paise", r.get("amount_paise"), f"{amount_issue} amount retained as blank")
                else:
                    gateway_summary["amount_total_rs"] += Decimal(amount_rs)
                if time_issue:
                    gateway_summary[f"{time_issue}_timestamp_rows"] += 1
                    flag("gateway_payments", file, row_no, payment_id, "created_at_epoch", r.get("created_at_epoch"), f"{time_issue} timestamp retained without conversion")
                elif utc:
                    gateway_date_min = min(gateway_date_min, utc) if gateway_date_min else utc
                    gateway_date_max = max(gateway_date_max, utc) if gateway_date_max else utc
                if settlement_id and not SETTLEMENT_ID_RE.fullmatch(settlement_id):
                    flag("gateway_payments", file, row_no, payment_id, "settlement_id", settlement_id, "settlement ID format needs review")
                gateway_statuses[status or "(blank)"] += 1
                gateway_methods[method or "(blank)"] += 1
                writer.writerow({"payment_id": payment_id, "invoice_ref_raw": ref_raw, "invoice_ref": invoice_ref,
                                 "amount_rs": amount_rs, "status": status, "created_at_epoch": (r.get("created_at_epoch") or "").strip(),
                                 "created_at_utc": utc, "created_at_ist": ist, "method": method, "settlement_id": settlement_id,
                                 "source_file": file.name, "source_row": row_no})
    profile["tables"]["gateway_payments"] = {
        "source_files": [p.name for p in gateway_files], "rows": gateway_summary["rows"],
        "repeated_header_rows_removed": gateway_summary["repeated_header_rows_removed"],
        "primary_key": "payment_id", "duplicate_payment_id_rows": payment_id_duplicates,
        "created_at_utc_min": gateway_date_min, "created_at_utc_max": gateway_date_max,
        "amount_total_rs_over_nonblank_valid_rows": f"{gateway_summary['amount_total_rs']:.2f}",
        "blank_amount_rows": gateway_summary["blank_amount_rows"], "invalid_amount_rows": gateway_summary["invalid_amount_rows"],
        "blank_timestamp_rows": gateway_summary["blank_timestamp_rows"], "invalid_timestamp_rows": gateway_summary["invalid_timestamp_rows"],
        "status_counts": dict(gateway_statuses), "method_counts": dict(gateway_methods),
        "invoice_reference_normalization": "trim outer whitespace and uppercase; raw value retained in invoice_ref_raw",
    }
    accounting.append({"dataset": "gateway_payments", "source_files": len(gateway_files), "input_rows_excluding_repeated_headers": gateway_summary["rows"],
                       "cleaned_rows": gateway_summary["rows"], "rejected_rows": 0,
                       "repeated_header_rows_removed": gateway_summary["repeated_header_rows_removed"],
                       "unit": "gateway payment attempts", "decision": "Retain successful and failed attempts; paise to rupees; preserve raw and normalized invoice reference; convert epoch to UTC and IST."})

    settlement_cols = ["settlement_id", "amount_rs", "fees_rs", "tax_rs", "utr", "created_at_epoch", "created_at_utc", "created_at_ist", "status", "source_file", "source_row"]
    settlement_path = output / "settlements.csv"
    settlement_summary = {"rows": 0, "repeated_header_rows_removed": 0, "amount_total_rs": Decimal(0), "fees_total_rs": Decimal(0), "tax_total_rs": Decimal(0)}
    settlement_ids = set()
    settlement_id_duplicates = 0
    settlement_statuses = Counter()
    settlement_date_min = settlement_date_max = ""
    with settlement_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=settlement_cols)
        writer.writeheader()
        for file in settlement_files:
            for row_no, r in read_source(file):
                if r is None:
                    settlement_summary["repeated_header_rows_removed"] += 1
                    continue
                settlement_summary["rows"] += 1
                settlement_id = (r.get("settlement_id") or "").strip()
                status = (r.get("status") or "").strip().lower()
                if not settlement_id:
                    flag("settlements", file, row_no, settlement_id, "settlement_id", "", "blank settlement ID retained")
                elif not SETTLEMENT_ID_RE.fullmatch(settlement_id):
                    flag("settlements", file, row_no, settlement_id, "settlement_id", settlement_id, "settlement ID format needs review")
                if settlement_id in settlement_ids:
                    settlement_id_duplicates += 1
                    flag("settlements", file, row_no, settlement_id, "settlement_id", settlement_id, "duplicate settlement ID retained")
                settlement_ids.add(settlement_id)
                converted = {}
                for raw_field, out_field in (("amount_paise", "amount_rs"), ("fees_paise", "fees_rs"), ("tax_paise", "tax_rs")):
                    converted[out_field], issue = money(r.get(raw_field), "paise")
                    if issue:
                        flag("settlements", file, row_no, settlement_id, raw_field, r.get(raw_field), f"{issue} value retained as blank")
                    else:
                        settlement_summary[out_field.replace("_rs", "_total_rs")] += Decimal(converted[out_field])
                utc, ist, time_issue = epoch_times(r.get("created_at_epoch"))
                if time_issue:
                    flag("settlements", file, row_no, settlement_id, "created_at_epoch", r.get("created_at_epoch"), f"{time_issue} timestamp retained without conversion")
                else:
                    settlement_date_min = min(settlement_date_min, utc) if settlement_date_min else utc
                    settlement_date_max = max(settlement_date_max, utc) if settlement_date_max else utc
                settlement_statuses[status or "(blank)"] += 1
                writer.writerow({"settlement_id": settlement_id, **converted, "utr": (r.get("utr") or "").strip(),
                                 "created_at_epoch": (r.get("created_at_epoch") or "").strip(), "created_at_utc": utc,
                                 "created_at_ist": ist, "status": status, "source_file": file.name, "source_row": row_no})
    profile["tables"]["settlements"] = {
        "source_files": [p.name for p in settlement_files], "rows": settlement_summary["rows"],
        "repeated_header_rows_removed": settlement_summary["repeated_header_rows_removed"],
        "primary_key": "settlement_id", "duplicate_settlement_id_rows": settlement_id_duplicates,
        "created_at_utc_min": settlement_date_min, "created_at_utc_max": settlement_date_max,
        "amount_total_rs": f"{settlement_summary['amount_total_rs']:.2f}",
        "fees_total_rs": f"{settlement_summary['fees_total_rs']:.2f}",
        "tax_total_rs": f"{settlement_summary['tax_total_rs']:.2f}", "status_counts": dict(settlement_statuses),
    }
    accounting.append({"dataset": "settlements", "source_files": len(settlement_files), "input_rows_excluding_repeated_headers": settlement_summary["rows"],
                       "cleaned_rows": settlement_summary["rows"], "rejected_rows": 0,
                       "repeated_header_rows_removed": settlement_summary["repeated_header_rows_removed"],
                       "unit": "settlement rows", "decision": "Retain each settlement; paise to rupees; convert epoch to UTC and IST."})

    profile["scope_note"] = (
        "All supplied finance periods are included so later analysis can inspect late payment and settlement timing. "
        "The handbook's 'second quarter' year should be confirmed during analysis; cleaning does not filter to a quarter."
    )
    profile["rows_retained_with_issues"] = len(issues)
    (output / "profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(output / "input_clean_rejected.csv",
              ["dataset", "source_files", "input_rows_excluding_repeated_headers", "cleaned_rows", "rejected_rows", "repeated_header_rows_removed", "unit", "decision"], accounting)
    write_csv(issue_path,
              ["dataset", "source_file", "source_row", "record_id", "field", "observed_value", "issue"], issues)
    issue_counts = Counter((r["dataset"], r["field"], r["issue"]) for r in issues)
    write_csv(output / "quality_issue_summary.csv",
              ["dataset", "field", "issue", "records_flagged"],
              [{"dataset": key[0], "field": key[1], "issue": key[2], "records_flagged": count}
               for key, count in sorted(issue_counts.items())])
    decisions = [
        {"decision_id": "C001", "area": "scope", "decision": "Clean only invoice, gateway-payment, and settlement sources into cleaned_brief_c/.", "rationale": "These are the financial records required for Brief C's invoice-to-collected bridge.", "impact": "The existing cleaned/ pack and all non-finance tables remain unchanged."},
        {"decision_id": "C002", "area": "period", "decision": "Retain all supplied finance periods; do not filter during cleaning.", "rationale": "Quarterly timing and late payments require rows outside the target invoice quarter; handbook wording does not specify a year.", "impact": "The analysis can select and document its quarter after confirming it with the team/COO."},
        {"decision_id": "C003", "area": "money", "decision": "Convert paise to exact two-decimal INR using Decimal; retain invoice amounts as INR.", "rationale": "The sources use different units and finance totals must avoid float rounding.", "impact": "All normalized money fields end in _rs."},
        {"decision_id": "C004", "area": "invoice-reference mapping", "decision": "Trim and uppercase gateway notes_invoice_ref; preserve the original reference alongside it.", "rationale": "Case and outer whitespace can be normalized safely while keeping an audit trail.", "impact": "No fuzzy, amount/date, or numeric-only mapping is performed during cleaning."},
        {"decision_id": "C005", "area": "payment attempts", "decision": "Keep failed and captured gateway attempts and retain repeated IDs/references with flags.", "rationale": "Failed attempts and multiple attempts are relevant to classifying the bridge; key repetition alone is not proof of a duplicate.", "impact": "The later analysis must distinguish captured payments from failed attempts and avoid double-counting."},
        {"decision_id": "C006", "area": "timestamps", "decision": "Preserve the source epoch and add explicit UTC and Asia/Kolkata timestamps.", "rationale": "The brief asks how much of the difference is timing across a quarter boundary.", "impact": "Quarter assignment can be made consistently in India local time, with UTC retained for traceability."},
        {"decision_id": "C007", "area": "personal data", "decision": "Exclude patient_id and patient names; retain booking_id only as an invoice-level validation key.", "rationale": "Patient identity is not required for money reconciliation; booking ID can test the one-invoice-per-visit assumption.", "impact": "The finance-only clean pack contains no patient names or patient IDs."},
        {"decision_id": "C008", "area": "row retention", "decision": "Retain all source records; flag missing or invalid values and repeated keys rather than deleting them.", "rationale": "Finance needs a complete, auditable bridge and unmatched lists.", "impact": "Cleaned counts reconcile to input rows after separately counting repeated headers."},
    ]
    write_csv(output / "decisions_log.csv", list(decisions[0]), decisions)
    print(f"Brief C finance-only clean pack written to: {output}")
    for name, info in profile["tables"].items():
        print(f"{name}: {info['rows']:,} rows; {info['repeated_header_rows_removed']:,} repeated headers; duplicate primary-key rows={info.get('duplicate_invoice_id_rows', info.get('duplicate_payment_id_rows', info.get('duplicate_settlement_id_rows', 0))):,}")
    print(f"Data-quality issues retained and logged: {len(issues):,}; source rows rejected: 0")
    print("No files in cleaned/ or the raw source folders were changed.")


if __name__ == "__main__":
    main()
