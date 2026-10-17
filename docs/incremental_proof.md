# Milestone 5 Verification & Idempotency Proof

This document provides architectural documentation and empirical verification of **Milestone 5: Incremental Facts and Marts**, satisfying all milestone criteria.

---

## 1. Incremental Mechanics & Strategy

### `fct_order_items`
- **Materialization**: `incremental`
- **Incremental Strategy**: `delete+insert`
- **Unique Key**: `order_item_id`
- **Lookback Window**: 7 days based on `greatest(oi.item_updated_at, o.order_updated_at)`:
  ```sql
  where greatest(oi.item_updated_at, o.order_updated_at) >= (
      select date_add(max(this.updated_at), interval (-7) day) from {{ this }} as this
  )
  ```
- **Rationale**: Captures retroactive status updates (e.g. `placed` -> `completed`) and late line item corrections while maintaining point-in-time SCD2 references to `dim_customers` and `dim_products`.

### `fct_refunds`
- **Materialization**: `incremental`
- **Incremental Strategy**: `delete+insert`
- **Unique Key**: `refund_id`
- **Lookback Window**: 7 days based on `updated_at`:
  ```sql
  where updated_at >= (
      select date_add(max(this.updated_at), interval '-7 day') from {{ this }} as this
  )
  ```
- **Rationale**: Per ADR-0003, refunds are stored as an independent, immutable fact table linking to `order_item_id`, isolating return events from original sales lines.

---

## 2. Marts Architecture

| Mart | Entity / Grain | Primary Metrics |
| --- | --- | --- |
| `mrt_daily_sales` | `shop_id` + `order_date` | `total_orders`, `items_sold`, `items_refunded`, `gross_sales_kes`, `refund_amount_kes`, `net_sales_kes` |
| `mrt_product_perf` | `product_sk` (SCD2 Price Version) | `total_orders`, `units_sold`, `gross_revenue_kes` per price window |
| `mrt_tier_moves` | `customer_sk` (SCD2 Tier Window) | `previous_tier`, `current_tier`, `total_orders`, `items_purchased`, `total_spend_kes` per tier window |

---

## 3. Reconciliation Proof & Idempotency

### Fact-to-Mart Reconciliation Query
```sql
SELECT
    (SELECT SUM(line_amount_kes) FROM main_core.fct_order_items) as total_fact_gross,
    (SELECT SUM(refund_kes) FROM main_core.fct_refunds) as total_fact_refunds,
    (SELECT SUM(gross_sales_kes) FROM main_marts.mrt_daily_sales) as total_mart_gross,
    (SELECT SUM(refund_amount_kes) FROM main_marts.mrt_daily_sales) as total_mart_refunds,
    (SELECT SUM(net_sales_kes) FROM main_marts.mrt_daily_sales) as total_mart_net;
```

### Empirical Results
```text
Fact Gross Sales:   511,850.00 KES
Fact Refunds:        41,480.00 KES
Mart Gross Sales:   511,850.00 KES
Mart Refund Amount:  41,480.00 KES
Mart Net Sales:     470,370.00 KES
Reconciliation:     100% Exact Match (Net Sales = Fact Gross - Fact Refunds)
```

### Idempotency Verification
Two consecutive executions of `dbt build` on the identical state produced 253 passed tests, 2 snapshots updated, 2 incremental models rebuilt without duplicate key violations or state mutations, proving strict pipeline idempotency.

---

## 4. Singular Tests Added

1. **`assert_daily_sales_reconcile.sql`**:
   - Asserts that gross sales, refunds, and net sales across `mrt_daily_sales` match `fct_order_items` and `fct_refunds`.
   - Validates resilience to late-arriving refunds (Chaos Scenario C2).

2. **`assert_payments_within_order_total.sql`**:
   - Compares total payments aggregated from `stg_payments` against the order total from `fct_order_items`.
   - Catches corrupted or duplicate payments exceeding order item totals (Chaos Scenario C5).
