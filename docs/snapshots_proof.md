# dukastack: Snapshot Verification Proof (Milestone 3)

This document provides formal proof of Slowly Changing Dimensions Type 2 (SCD2) history tracking via dbt snapshots on DuckDB.

---

## 1. Customer Loyalty Tier Snapshot (`snap_customers`)

- **Table**: `snapshots.snap_customers`
- **Tracked Natural Key**: `customer_id`
- **Strategy**: `timestamp` on `updated_at`
- **Verification Criterion**: At least one customer exhibits $\ge 3$ loyalty tier versions with strictly contiguous valid ranges (`dbt_valid_to` of version $N$ equals `dbt_valid_from` of version $N+1$).

### Query: `docs/queries/customer_tier_history.sql`

```sql
select
    customer_id,
    customer_name,
    county,
    loyalty_tier,
    dbt_valid_from,
    dbt_valid_to,
    case
        when dbt_valid_to is null then true
        else false
    end as is_current
from {{ ref('snap_customers') }}
where customer_id = 'CUST-0039'
order by dbt_valid_from asc;
```

### Result

| customer_id | customer_name | county | loyalty_tier | dbt_valid_from | dbt_valid_to | is_current |
| --- | --- | --- | --- | --- | --- | --- |
| CUST-0039 | Amina Wanjala | Kisumu | silver | 2026-09-01 08:00:00 | 2026-09-10 08:00:00 | False |
| CUST-0039 | Amina Wanjala | Kisumu | gold | 2026-09-10 08:00:00 | 2026-09-11 08:00:00 | False |
| CUST-0039 | Amina Wanjala | Kisumu | basic | 2026-09-11 08:00:00 | 2026-09-21 08:00:00 | False |
| CUST-0039 | Amina Wanjala | Kisumu | silver | 2026-09-21 08:00:00 | NULL | True |

**Observations**:

- Customer `CUST-0039` transitioned through 4 distinct tier versions (`silver` $\to$ `gold` $\to$ `basic` $\to$ `silver`).
- Validity timestamps have zero gaps and zero overlaps across version boundaries.
- The active tier version has `dbt_valid_to IS NULL` and `is_current = True`.

---

## 2. Product Unit Price Snapshot (`snap_products`)

- **Table**: `snapshots.snap_products`
- **Tracked Natural Key**: `product_id`
- **Strategy**: `timestamp` on `updated_at`

### Result for Product `PRD-004` (Tusker Lager 500ml)

| product_id | product_name | category | unit_price_kes | dbt_valid_from | dbt_valid_to | is_current |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-004 | Tusker Lager 500ml | Beverages | 220.00 | 2026-09-01 08:00:00 | 2026-09-10 08:00:00 | False |
| PRD-004 | Tusker Lager 500ml | Beverages | 245.00 | 2026-09-10 08:00:00 | 2026-09-12 08:00:00 | False |
| PRD-004 | Tusker Lager 500ml | Beverages | 265.00 | 2026-09-12 08:00:00 | 2026-09-17 08:00:00 | False |
| PRD-004 | Tusker Lager 500ml | Beverages | 235.00 | 2026-09-17 08:00:00 | NULL | True |

---

## 3. Automated Singular Data Quality Tests

1. **`assert_scd2_no_overlap`**:
   - Ensures mathematical non-overlap for every entity across all validity windows.
   - Status: **PASSED** (0 violating records).
2. **`assert_snapshot_matches_source`**:
   - Asserts that active snapshot versions match current operational state, catching retroactive backdated changes (Chaos Scenario C1).
   - Status: **PASSED** (0 mismatches in baseline operational runs).
