{% docs __overview__ %}

# Welcome to dukastack 🏬🇰🇪

**dukastack** is a local, zero-cost retail analytics warehouse modeled over point-of-sale (POS) data from a fictional chain of Kenyan *dukas* (neighborhood retail shops). It is built with **dbt** (`dbt-core` + `dbt-duckdb`), **DuckDB**, and **Dagster**.

---

## 🎯 The Core Problem & Value Proposition

In legacy and high-volume retail POS systems, transactions record *what* was sold and in what quantity, but commonly omit historical pricing and customer loyalty tiers at the moment of sale. If a customer upgrades from `basic` to `silver` or a product price increases from KES 120 to KES 150, a naive join to the current catalog distorts historical revenue and customer lifetime value.

**dukastack solves this through tested Slowly Changing Dimensions Type 2 (SCD2)**:
1. Every price change and loyalty tier transition is captured in continuous, non-overlapping snapshot validity windows (`dbt_valid_from` to `dbt_valid_to`).
2. An **as-of join macro** (`macros/as_of_join.sql`) reconstructs point-in-time state for every order item line, guaranteeing that every transaction receives the exact price and customer tier active at `order_ts`.
3. Customer refunds arriving up to 7 days post-transaction are modeled as an immutable, separate fact (`fct_refunds`) and reconciled against sales in marts.

---

## 🏗️ Architecture & Data Layers

Data moves strictly downstream through five layers within a single local DuckDB warehouse:

```text
[ Operational POS Simulator ]
              │
              ▼
    1. Raw (raw.*)
              │
              ├───► Snapshots (snapshots.snap_*)  ───┐
              │                                      │
              ▼                                      ▼
    2. Staging (main_staging.stg_*) ────► 3. Core Star Schema (main_core.*)
                                                     │
                                                     ▼
                                            4. Marts (main_marts.mrt_*)
                                                     │
                                                     ▼
                                            5. Business Exposures (BQ-1 .. BQ-5)
```

### 1. Raw Layer (`raw`)
- Ingested directly from the POS operational simulator via `simulator.loader` into DuckDB.
- Tables: `shops`, `customers`, `products`, `orders`, `order_items`, `payments`, `refunds`.
- Each record receives a warehouse metadata ingestion timestamp `_loaded_at`.
- Immutable source of truth governed by dbt `source freshness` monitors.

### 2. Staging Layer (`main_staging`)
- 1-to-1 lightweight views over raw tables.
- Standardizes data types, renames columns to warehouse standards (`_id`, `_kes`, `_ts`, `_date`), and casts monetary values to `DECIMAL(12, 2)`.
- Models: `stg_shops`, `stg_customers`, `stg_products`, `stg_orders`, `stg_order_items`, `stg_payments`, `stg_refunds`.
- Contains `unique` and `not_null` constraints on primary keys, plus `accepted_values` tests on statuses and payment methods.

### 3. Snapshots Layer (`snapshots`)
- Captures point-in-time state changes using dbt snapshot timestamp strategy:
  - `snap_customers`: Tracks customer `loyalty_tier` progression (`basic` -> `silver` -> `gold`).
  - `snap_products`: Tracks retail `unit_price_kes` revisions across product catalog SKUs.
- Tested with `assert_scd2_no_overlap` and `assert_snapshot_matches_source` to prevent timestamp gaps or collision anomalies.

### 4. Core Star Schema Layer (`main_core`)
- Materialized as physical tables with surrogate keys generated via `dbt_utils.generate_surrogate_key`:
  - `dim_shops`: Type 1 physical retail location dimension.
  - `dim_customers`: SCD Type 2 customer loyalty dimension with surrogate key `customer_sk`.
  - `dim_products`: SCD Type 2 product catalog dimension with surrogate key `product_sk`.
  - `dim_date`: Calendar date spine dimension supporting daily time-series analysis.
  - `fct_order_items`: Incremental sales fact table with point-in-time surrogate foreign keys resolved at transaction time via as-of joins.
  - `fct_refunds`: Incremental refund fact table linked to original sales lines.

### 5. Marts Layer (`main_marts`)
- Enforced, contract-backed aggregated reporting models serving analytics personas:
  - `mrt_daily_sales`: Daily shop performance, gross sales, refund reconciliations, and net revenue.
  - `mrt_product_perf`: Product sales volume, orders, and gross revenue broken down per SCD2 price version.
  - `mrt_tier_moves`: Customer loyalty cohort transitions and spend velocity across SCD2 tier windows.

---

## 🧭 Where to Start

1. **Lineage Graph**:
   Click the **Lineage Graph** button (bottom right) to see the end-to-end dependency flow from `raw` sources to core dimensions, incremental facts, marts, and business exposures.
2. **Business Exposures**:
   Explore the five business questions configured under the **Exposures** tab:
   - **BQ-1**: Shop & Product Revenue and Margin (`mrt_daily_sales`, `mrt_product_perf`, `fct_order_items`)
   - **BQ-2**: Stockout Risk & Inventory Velocity (`mrt_product_perf`, `mrt_daily_sales`)
   - **BQ-3**: Price Change Impact & SCD2 Elasticity (`mrt_product_perf`, `dim_products`)
   - **BQ-4**: Slow Movers & Low-Velocity Catalog (`mrt_product_perf`)
   - **BQ-5**: Warehouse Freshness & Pipeline Latency (`mrt_daily_sales`, `snap_customers`, `snap_products`)
3. **Data Quality & Contract Verification**:
   Check model definitions and column documentation to review data contracts, primary key constraints, foreign key relationships, and singular tests (`assert_daily_sales_reconcile`, `assert_payments_within_order_total`).
4. **Dagster Orchestration**:
   Start the Dagster UI (`make dagster`) to view the interactive software-defined asset graph, daily automated pipeline schedules, and real-time asset checks.

{% enddocs %}
