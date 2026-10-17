# dukastack: Chaos Scenarios (What We Broke on Purpose)

Every test in dukastack exists because a specific failure justified it. The `chaos` simulator injects scenarios C1 through C6 into a copy of the database to prove that our data quality suite catches real-world data corruption.

## Chaos Scenario Matrix

| ID     | Scenario                     | Injection Mechanism                                                            | Caught By                                                                      | Severity |
| ------ | ---------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | -------- |
| **C1** | Retroactive price correction | Changes a product's price but back-dates `updated_at` before the last snapshot | `assert_snapshot_matches_source`: current snapshot row differs from source row | error    |
| **C2** | Late-arriving refund         | Writes a refund today for an order placed 5 days ago                           | Handled by 7-day lookback; verified by `assert_daily_sales_reconcile`          | error    |
| **C3** | Orphan order                 | Generates an order whose `customer_id` does not exist in `customers`           | `not_null` & `relationships` on `fct_order_items.customer_sk`                  | error    |
| **C4** | Duplicate customer row       | Inserts a duplicate row with the same `customer_id` and `updated_at`           | `unique` test on `stg_customers.customer_id`                                   | error    |
| **C5** | Overpaid order               | Writes payments exceeding total items amount                                   | `assert_payments_within_order_total`                                           | error    |
| **C6** | Skipped day                  | Advances 2 days between builds with same customer changing tier on both        | Dagster freshness check on `snap_customers`                                    | warn     |

## Detailed Descriptions

### C1: Retroactive Price Correction

- **Problem**: In real retail systems, a price correction is sometimes applied retroactively in the operational database.
- **Why it matters**: Timestamp-based snapshots assume `updated_at` is monotonically increasing. Backdated edits bypass standard snapshot tracking.
- **Verification**: `assert_snapshot_matches_source.sql` queries the latest source state against the snapshot's current record (`dbt_valid_to is null`) and raises an error on discrepancy.

### C2: Late-Arriving Refund

- **Problem**: Customers return items days after the transaction.
- **Why it matters**: If fact tables are incrementally loaded without lookback, older periods lose refund reconciliation.
- **Verification**: Incremental models use `delete+insert` with a 7-day window. `assert_daily_sales_reconcile.sql` ensures daily net sales match all recorded refunds.

### C3: Orphan Order

- **Problem**: POS transaction logged without a valid customer ID.
- **Why it matters**: Breaks referential integrity and silently corrupts customer analytics.
- **Verification**: `as_of_join` uses `LEFT JOIN`. Unmatched customers produce `NULL` keys, triggering failure in the dbt `not_null` test.

### C4: Duplicate Customer Row

- **Problem**: Double write from POS sync service.
- **Why it matters**: Multiplies snapshot rows and produces Cartesian products in downstream marts.
- **Verification**: Primary key uniqueness test on `stg_customers`.

### C5: Overpaid Order

- **Problem**: Duplicate payment record or corrupted payment sum.
- **Why it matters**: Distorts cash reconciliations and payment provider audits.
- **Verification**: Singular test `assert_payments_within_order_total.sql`.

### C6: Skipped Day

- **Problem**: Pipeline pipeline run was missed (e.g. outage or downtime).
- **Why it matters**: Intermediate tier changes within the skipped day are lost in daily snapshots.
- **Verification**: Dagster asset check flags pipeline lag; documented limitation in ADR-0002.
