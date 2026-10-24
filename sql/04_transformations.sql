-- The methods, as CTE pipelines a finance analyst can read top to bottom.
-- Every query states its grain and its denominator in the comment above it.

-- 1. The tree. Grain: one row per half-year. Denominator for rates: the H1 2025 row.
WITH halves AS (
    SELECT CASE WHEN slot_at >= '2025-01-01' AND slot_at < '2025-07-01' THEN 'H1_2025'
                WHEN slot_at >= '2026-01-01' AND slot_at < '2026-07-01' THEN 'H1_2026' END AS half,
           booking_id, person_id, n_tests
    FROM bookings
    WHERE status_at_export IS DISTINCT FROM 'rescheduled'
),
agg AS (
    SELECT half, sum(n_tests) AS tests, count(*) AS visits, count(DISTINCT person_id) AS people
    FROM halves WHERE half IS NOT NULL GROUP BY half
)
SELECT half, tests, visits, people,
       round(1.0 * visits / people, 4) AS visits_per_person,
       round(1.0 * tests / visits, 4) AS tests_per_visit
FROM agg ORDER BY half;

-- 2. Monthly rollup with window functions. Grain: one row per city per month.
--    LAG gives the previous month in the same city; the running total is deterministic because month is unique within city.
WITH monthly AS (
    SELECT city, month, sum(n_tests) AS tests
    FROM bookings
    WHERE status_at_export IS DISTINCT FROM 'rescheduled'
    GROUP BY city, month
)
SELECT city, month, tests,
       LAG(tests) OVER (PARTITION BY city ORDER BY month) AS prev_month,
       round(100.0 * (tests - LAG(tests) OVER (PARTITION BY city ORDER BY month)) / NULLIF(LAG(tests) OVER (PARTITION BY city ORDER BY month), 0), 1) AS mom_pct,
       sum(tests) OVER (PARTITION BY city ORDER BY month ROWS UNBOUNDED PRECEDING) AS running_total,
       RANK() OVER (PARTITION BY month ORDER BY tests DESC) AS rank_in_month
FROM monthly
ORDER BY city, month;

-- 3. Actual against plan. Grain: one row per city per month of 2026 H1.
SELECT p.city, p.month, p.target_tests, coalesce(m.tests, 0) AS actual_tests,
       round(100.0 * (coalesce(m.tests, 0) - p.target_tests) / p.target_tests, 1) AS gap_pct
FROM plan p
LEFT JOIN (SELECT city, month, sum(n_tests) AS tests FROM bookings WHERE status_at_export IS DISTINCT FROM 'rescheduled' GROUP BY city, month) m
       ON m.city = p.city AND m.month = p.month
ORDER BY p.city, p.month;

-- 4. H1 2026 invoice balances. Amounts use captured payments through 30 June.
WITH h1 AS (
    SELECT invoice_id, amount_rs FROM invoices WHERE invoice_date >= '2026-01-01' AND invoice_date < '2026-07-01'
),
paid AS (
    SELECT invoice_id,
           sum(amount_rs) FILTER (WHERE status = 'captured' AND created_at < '2026-07-01') AS paid_rs,
           count(*) FILTER (WHERE status = 'captured' AND created_at < '2026-07-01') AS captures
    FROM payments GROUP BY invoice_id
)
SELECT count(*) AS invoices, sum(q.amount_rs) AS invoiced_rs,
       count(*) FILTER (WHERE p.paid_rs IS NULL) AS no_capture_invoices,
       sum(q.amount_rs) FILTER (WHERE p.paid_rs IS NULL) AS no_capture_rs,
       sum(greatest(q.amount_rs - coalesce(p.paid_rs, 0), 0)) AS positive_balance_rs,
       count(*) FILTER (WHERE p.captures > 1) AS invoices_with_multiple_captures
FROM h1 q LEFT JOIN paid p USING (invoice_id);

-- 5. H1 captured payments without a matching invoice.
SELECT p.payment_id, p.notes_invoice_ref, p.invoice_id AS normalised_ref, p.amount_rs
FROM payments p
LEFT JOIN invoices i ON i.invoice_id = p.invoice_id
WHERE p.status = 'captured' AND p.created_at >= '2026-01-01' AND p.created_at < '2026-07-01'
  AND i.invoice_id IS NULL
ORDER BY p.amount_rs DESC;

-- 6. Retries: invoices with more than one payment row, split by status. Grain: one row per invoice.
SELECT invoice_id, count(*) AS payment_rows,
       sum(CASE WHEN status = 'captured' THEN 1 ELSE 0 END) AS captured_rows,
       sum(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_rows
FROM payments
GROUP BY invoice_id
HAVING count(*) > 1
ORDER BY captured_rows DESC, payment_rows DESC
LIMIT 20;
