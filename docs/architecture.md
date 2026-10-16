# dukastack: System Architecture

dukastack is an end-to-end local analytics warehouse for point-of-sale data from a fictional chain of Kenyan duka (small retail shops).

## Architecture Overview

All layers reside in a single DuckDB database file (`data/dukastack.duckdb`), orchestrated by Dagster and verified in GitHub Actions CI.

```text
+-------------------------------------------------------------------------+
|                              Dagster                                    |
|              (Asset-based orchestration, daily schedules)               |
+-------------------------------------------------------------------------+
                                    |
                                    v
+------------------+     +--------------------+     +---------------------+
|    Simulator     | --> |   DuckDB (raw)     | --> |   dbt Staging       |
| (Python + Seed)  |     | (Shops, Customers, |     | (Views: 1-to-1 with |
|                  |     |  Products, Orders) |     |  raw, typed/cleaned)|
+------------------+     +--------------------+     +---------------------+
                                                       |
                                                       v
+------------------+     +--------------------+     +---------------------+
|   dbt Marts      | <-- |     dbt Core       | <-- |    dbt Snapshots    |
| (Daily Sales,    |     | (Star Schema: Fact |     | (SCD Type 2 tables: |
|  Product Perf,   |     |  & Dim tables with |     |  snap_customers,    |
|  Tier Moves)     |     |  as-of joins)      |     |  snap_products)     |
+------------------+     +--------------------+     +---------------------+
```

## Layer Definitions & Contracts

1. **raw (`raw` schema)**
   - Populated exclusively by `simulator/loader.py`.
   - Immutable historical load, stamped with `_loaded_at`.
   - dbt never writes to `raw`.

2. **staging (`staging` schema)**
   - One view per raw table (`stg_*`).
   - Renaming, casting, trimming only. No business logic or joins.
   - Enforces `unique` and `not_null` primary keys.

3. **snapshots (`snapshots` schema)**
   - Implements SCD Type 2 tracking for:
     - `customers`: loyalty tier (`basic`, `silver`, `gold`).
     - `products`: unit price (`unit_price_kes`).
   - Built using dbt snapshot timestamp strategy on `updated_at`.

4. **core (`core` schema)**
   - Star schema tables:
     - `dim_shops`: Type 1 dimension.
     - `dim_customers`: SCD Type 2 dimension with surrogate keys.
     - `dim_products`: SCD Type 2 dimension with surrogate keys.
     - `dim_date`: Generated calendar date spine.
     - `fct_order_items`: Incremental sales fact table with point-in-time dimensions.
     - `fct_refunds`: Incremental refunds fact table.
   - Joins use the `as_of_join` macro to reconstruct accurate historical prices and tiers.

5. **marts (`marts` schema)**
   - Business-facing analytical models:
     - `mrt_daily_sales`: Daily shop revenue, net of refunds.
     - `mrt_product_perf`: Product movement and price change elasticity.
     - `mrt_tier_moves`: Customer loyalty tier transitions and spending behavior.
   - Marts read only from core models.
