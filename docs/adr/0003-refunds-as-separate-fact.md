# ADR 0003: Refunds as a Separate Fact Table

## Context
Customer returns and refunds arrive up to 7 days after the original purchase. We must decide how refunds are modeled and reconciled against sales.

## Considered Alternatives
1. In-place mutation: Update `fct_order_items` quantity and net amount directly.
2. Separate fact table: Maintain immutable `fct_order_items` and create `fct_refunds`.

## Decision
We model refunds as an independent, incremental fact table **`fct_refunds`** referencing `order_item_id`.

## Consequences
- **Immutability**: Original sales transactions are never modified or deleted, maintaining complete auditability.
- **Resilience to Late Arrivals**: Incremental updates with a 7-day lookback window process refunds seamlessly without full-table recomputations.
- **Explicit Reconciliation**: Marts (`mrt_daily_sales`) combine facts explicitly, verified by `assert_daily_sales_reconcile`.
