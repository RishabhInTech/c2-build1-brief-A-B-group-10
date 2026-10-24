"""Reconcile H1 invoices to captured payments and settlement rows."""

import argparse
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd


def money(values):
    return values.map(lambda value: Decimal(str(value or "0")))


def rupees(value):
    return f"{Decimal(value):.2f}"


def crores(value):
    return f"{Decimal(value) / 10000000:.4f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/clean/brief_c")
    parser.add_argument("--output-dir", default="outputs/brief_c")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--observation-cutoff", default="2026-07-15")
    parser.add_argument("--action-dir", default="data/clean/brief_c/actions")
    args = parser.parse_args()

    data, output, action_dir = map(Path, (args.data_dir, args.output_dir, args.action_dir))
    output.mkdir(parents=True, exist_ok=True)
    action_dir.mkdir(parents=True, exist_ok=True)
    def read(name):
        return pd.read_csv(data / name, dtype=str, keep_default_na=False)

    invoices = read("invoices.csv")
    payments = read("gateway_payments.csv")
    settlements = read("settlements.csv")

    invoices["amount_value"] = money(invoices["amount_rs"])
    payments["amount_value"] = money(payments["amount_rs"])
    for source, target in (("amount_rs", "gross_value"), ("fees_rs", "fees_value"), ("tax_rs", "tax_value")):
        settlements[target] = money(settlements[source])

    invoices["canonical"] = invoices["invoice_id"].str.replace("-", "", regex=False)
    payments["canonical"] = payments["invoice_ref"].str.replace("-", "", regex=False)
    canonical_counts = invoices.groupby("canonical")["invoice_id"].nunique()
    canonical_map = (invoices.drop_duplicates("canonical").set_index("canonical")["invoice_id"].to_dict())
    canonical_map = {key: value for key, value in canonical_map.items() if canonical_counts[key] == 1}
    invoice_ids = set(invoices["invoice_id"])
    payments["mapped_invoice_id"] = payments["invoice_ref"].where(payments["invoice_ref"].isin(invoice_ids))
    needs_map = payments["mapped_invoice_id"].isna()
    payments.loc[needs_map, "mapped_invoice_id"] = payments.loc[needs_map, "canonical"].map(canonical_map)

    start = pd.Timestamp(args.year, 1, 1, tz="Asia/Kolkata")
    end = pd.Timestamp(args.year + 1, 7, 1, tz="Asia/Kolkata")
    observe_end = pd.Timestamp(args.observation_cutoff, tz="Asia/Kolkata") + pd.Timedelta(days=1)
    start_utc, end_utc = start.tz_convert("UTC"), end.tz_convert("UTC")
    observe_utc = observe_end.tz_convert("UTC")
    invoices["invoice_date"] = pd.to_datetime(invoices["invoice_date"], errors="coerce")
    payments["payment_time"] = pd.to_datetime(payments["created_at_ist"], errors="coerce", utc=True)

    h1_invoices = invoices[(invoices["invoice_date"] >= start.tz_localize(None))
                           & (invoices["invoice_date"] < end.tz_localize(None))].copy()
    invoice_ids = set(h1_invoices["invoice_id"])
    matched = payments[(payments["status"] == "captured") & payments["mapped_invoice_id"].isin(invoice_ids)]
    by_close = matched[matched["payment_time"] < end_utc].groupby("mapped_invoice_id").agg(
        paid_value=("amount_value", "sum"), capture_rows=("payment_id", "size"))
    by_observation = matched[matched["payment_time"] < observe_utc].groupby("mapped_invoice_id").agg(
        observed_paid_value=("amount_value", "sum"))
    cohort = h1_invoices.set_index("invoice_id").join(by_close).join(by_observation)
    for col in ("paid_value", "observed_paid_value"):
        cohort[col] = cohort[col].map(lambda value: value if pd.notna(value) else Decimal(0))
    cohort["capture_rows"] = cohort["capture_rows"].fillna(0).astype("int64")

    no_capture = cohort["paid_value"] == 0
    partial = (cohort["paid_value"] > 0) & (cohort["paid_value"] < cohort["amount_value"])
    overpaid = cohort["paid_value"] > cohort["amount_value"]
    positive = (cohort["amount_value"] - cohort["paid_value"]).clip(lower=0)
    overcapture = (cohort["paid_value"] - cohort["amount_value"]).clip(lower=0)
    later_paid = no_capture & (cohort["observed_paid_value"] > 0)

    # These row-level lists stay in the ignored local data folder.
    open_rows = cohort[positive > 0].copy()
    open_rows["captured_amount_by_h1_end_rs"] = open_rows["paid_value"].map(rupees)
    open_rows["positive_balance_rs"] = positive[positive > 0].map(rupees)
    open_rows.reset_index()[["invoice_id", "invoice_date", "booking_id", "city", "channel", "amount_rs",
        "captured_amount_by_h1_end_rs", "positive_balance_rs", "capture_rows", "source_file", "source_row"]].to_csv(
            action_dir / "h1_invoice_positive_balances.csv", index=False)

    h1_payments = payments[payments["payment_time"].between(start_utc, end_utc, inclusive="left")]
    h1_captured = h1_payments[h1_payments["status"] == "captured"]
    h1_failed = h1_payments[h1_payments["status"] == "failed"]
    h1_unmatched = h1_captured[h1_captured["mapped_invoice_id"].isna()]
    h1_unmatched[["payment_id", "invoice_ref_raw", "invoice_ref", "amount_rs", "status", "method",
                 "settlement_id", "created_at_ist", "source_file", "source_row"]].to_csv(
        action_dir / "h1_unmatched_captures.csv", index=False)
    all_captured = payments[payments["status"] == "captured"]
    all_unmatched = all_captured[all_captured["mapped_invoice_id"].isna()]
    all_matched = all_captured[all_captured["mapped_invoice_id"].notna()]

    # Match settlement IDs separately; this does not establish bank receipt.
    settled_captures = all_captured[all_captured["settlement_id"].ne("")].groupby("settlement_id")["amount_value"].sum()
    settlements["captured_value"] = settlements["settlement_id"].map(settled_captures).map(
        lambda value: value if pd.notna(value) else Decimal(0))
    settlements["net_value"] = settlements["gross_value"] - settlements["fees_value"] - settlements["tax_value"]
    settlement_time = pd.to_datetime(settlements["created_at_ist"], utc=True)
    h1_settlements = settlements[settlement_time.between(start_utc, end_utc, inclusive="left")]

    payment_window = {
        "attempt_rows": len(h1_payments), "captured_rows": len(h1_captured),
        "captured_amount_rs": rupees(h1_captured["amount_value"].sum()),
        "failed_rows": len(h1_failed), "failed_attempt_amount_rs_not_receipts": rupees(h1_failed["amount_value"].sum()),
        "matched_capture_rows": int(h1_captured["mapped_invoice_id"].notna().sum()),
        "matched_capture_amount_rs": rupees(h1_captured.loc[h1_captured["mapped_invoice_id"].notna(), "amount_value"].sum()),
        "unmatched_capture_rows": len(h1_unmatched), "unmatched_capture_amount_rs": rupees(h1_unmatched["amount_value"].sum()),
    }
    settlement_gross = h1_settlements["gross_value"].sum()
    linked_captures = h1_settlements["captured_value"].sum()
    summary = {
        "period": f"{args.year}-H1",
        "h1_start_ist": start.isoformat(), "h1_end_exclusive_ist": end.isoformat(),
        "observation_cutoff_inclusive_ist": args.observation_cutoff,
        "reference_rule": "Exact invoice ID, else remove hyphens when the invoice key is unique.",
        "mapping": {
            "invoice_ids": invoices["invoice_id"].nunique(), "canonical_collisions": int((canonical_counts > 1).sum()),
            "mapped_gateway_rows": int(payments["mapped_invoice_id"].notna().sum()),
            "unmapped_gateway_rows": int(payments["mapped_invoice_id"].isna().sum()),
            "unmatched_captured_rows_all_observed": len(all_unmatched),
            "unmatched_captured_amount_rs_all_observed": rupees(all_unmatched["amount_value"].sum()),
            "unmatched_captured_rows_in_h1": len(h1_unmatched),
            "unmatched_captured_amount_rs_in_h1": rupees(h1_unmatched["amount_value"].sum()),
            "reference_format_counts": {str(k): int(v) for k, v in payments["invoice_ref"].str.replace(
                r"\d", "9", regex=True).value_counts().items()},
        },
        "all_supplied_periods": {
            "invoice_count": len(invoices), "invoice_amount_rs": rupees(invoices["amount_value"].sum()),
            "gateway_attempt_rows": len(payments), "captured_rows": len(all_captured),
            "captured_amount_rs": rupees(all_captured["amount_value"].sum()),
            "matched_captured_rows": len(all_matched),
            "matched_captured_amount_rs": rupees(all_matched["amount_value"].sum()),
            "unmatched_captured_rows": len(all_unmatched),
            "unmatched_captured_amount_rs": rupees(all_unmatched["amount_value"].sum()),
        },
        "invoice_cohort": {
            "invoice_count": len(cohort), "invoice_amount_rs": rupees(cohort["amount_value"].sum()),
            "matched_captured_attempt_rows_by_h1_end": int(cohort["capture_rows"].sum()),
            "matched_captured_amount_rs_by_h1_end": rupees(cohort["paid_value"].sum()),
            "invoices_with_any_capture_by_h1_end": int((cohort["paid_value"] > 0).sum()),
            "invoices_with_no_capture_by_h1_end": int(no_capture.sum()),
            "no_capture_invoice_amount_rs_by_h1_end": rupees(cohort.loc[no_capture, "amount_value"].sum()),
            "partially_paid_invoices_by_h1_end": int(partial.sum()),
            "partial_invoice_face_amount_rs": rupees(cohort.loc[partial, "amount_value"].sum()),
            "partial_unpaid_balance_rs": rupees(positive[partial].sum()),
            "overcaptured_invoices_by_h1_end": int(overpaid.sum()), "overcapture_rs": rupees(overcapture.sum()),
            "positive_invoice_balance_rs_by_h1_end": rupees(positive.sum()),
            "net_invoice_balance_rs_by_h1_end": rupees(cohort["amount_value"].sum() - cohort["paid_value"].sum()),
            "no_capture_invoices_with_capture_by_observation_cutoff": int(later_paid.sum()),
            "face_amount_rs_of_those_later_paid_invoices": rupees(cohort.loc[later_paid, "amount_value"].sum()),
            "remaining_positive_invoice_balance_rs_by_observation_cutoff": rupees(
                (cohort["amount_value"] - cohort["observed_paid_value"]).clip(lower=0).sum()),
            "remaining_positive_balance_invoice_count_by_observation_cutoff": int(
                (cohort["amount_value"] > cohort["observed_paid_value"]).sum()),
            "matched_capture_amount_rs_by_observation_cutoff": rupees(cohort["observed_paid_value"].sum()),
        },
        "payment_attempts_created_in_h1": payment_window,
        "settlement_period": {
            "settlement_rows": len(h1_settlements), "gross_rs": rupees(settlement_gross),
            "fees_rs": rupees(h1_settlements["fees_value"].sum()), "tax_rs": rupees(h1_settlements["tax_value"].sum()),
            "net_after_fees_tax_rs": rupees(h1_settlements["net_value"].sum()),
            "captured_attempts_linked_by_settlement_id_rs_all_payment_dates": rupees(linked_captures),
            "linked_captures_minus_settlement_gross_rs": rupees(linked_captures - settlement_gross),
            "interpretation": "Diagnostic only; confirm date coverage, bank and cash records with Finance.",
        },
        "limitations": [
            "H1 2026 is the requested focus period; confirm source completeness with Finance.",
            "No matched gateway payment does not prove permanent nonpayment.",
            "Malformed references stay unmatched; amount/date similarity is not used to guess identity.",
            "The settlement comparison is not a bank reconciliation.",
        ],
        "private_action_lists": [str(action_dir / "h1_invoice_positive_balances.csv"),
                                 str(action_dir / "h1_unmatched_captures.csv")],
    }
    (output / "finance_bridge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    all_period_rows = [
        ("Invoices, all supplied periods", len(invoices), invoices["amount_value"].sum()),
        ("Captured attempts, all supplied periods (gross)", len(all_captured), all_captured["amount_value"].sum()),
        ("Captured attempts with safe invoice match", len(all_matched), all_matched["amount_value"].sum()),
        ("Captured attempts without invoice match", len(all_unmatched), all_unmatched["amount_value"].sum()),
    ]
    pd.DataFrame([{"item": name, "rows": int(count), "amount_crore": crores(amount), "amount_rs": rupees(amount)}
                  for name, count, amount in all_period_rows]).to_csv(
                      output / "finance_all_period_summary.csv", index=False)

    rows = [
        ("H1 invoices", len(cohort), cohort["amount_value"].sum()),
        ("Captured attempts matched by H1 end", cohort["capture_rows"].sum(), cohort["paid_value"].sum()),
        ("Invoices with no matched capture by H1 end", no_capture.sum(), cohort.loc[no_capture, "amount_value"].sum()),
        ("Partially paid invoices by H1 end", partial.sum(), positive[partial].sum()),
        ("Overcaptured invoices by H1 end", overpaid.sum(), overcapture.sum()),
        ("Positive balances less overcaptures (diagnostic, not accounting net)", (positive > 0).sum(), cohort["amount_value"].sum() - cohort["paid_value"].sum()),
        ("Unmatched captured attempts created in H1", len(h1_unmatched), h1_unmatched["amount_value"].sum()),
        ("Failed attempts created in H1 (not receipts)", len(h1_failed), h1_failed["amount_value"].sum()),
        ("Unmatched captured attempts all observed", len(all_unmatched), all_unmatched["amount_value"].sum()),
    ]
    pd.DataFrame([{"bridge_item": name, "rows": int(count), "amount_crore": crores(amount), "amount_rs": rupees(amount)}
                  for name, count, amount in rows]).to_csv(output / "finance_bridge_summary.csv", index=False)
    print(f"Saved {args.year}-H1 bridge to {output}")
    print(json.dumps(summary["invoice_cohort"], indent=2))


if __name__ == "__main__":
    main()
