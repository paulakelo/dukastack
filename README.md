# dukastack

[![CI](https://github.com/paulakelo/dukastack/actions/workflows/ci.yml/badge.svg)](https://github.com/paulakelo/dukastack/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/dbt--docs-GitHub%20Pages-blue)](https://paulakelo.github.io/dukastack/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-yellow.svg)](https://duckdb.org/)
[![dbt](https://img.shields.io/badge/dbt-1.8+-FF694B.svg)](https://www.getdbt.com/)
[![Dagster](https://img.shields.io/badge/Dagster-1.8+-2563EB.svg)](https://dagster.io/)

A local, zero-cost analytics warehouse for point-of-sale data from a fictional chain of Kenyan *duka* (small retail shops), built with **dbt**, **DuckDB**, and **Dagster**.

dukastack demonstrates production-grade **Slowly Changing Dimensions (SCD Type 2) that remain strictly correct when product prices and customer loyalty tiers change**, backed by point-in-time joins, automated boundary tests, and deliberately injected chaos scenarios.

---

## Features

- **Point-in-Time SCD Type 2 History**: Reconstructs the exact product price and customer loyalty tier in force at the precise second a sale occurred, even when the operational POS never recorded historical prices.
- **Single-File Zero-Cost OLAP Engine**: Powered by an embedded DuckDB database file, requiring zero cloud bills, zero background daemon servers, and running identically on local developer machines and in CI.
- **Deterministic Event Simulation**: Generates reproducible retail transactions, daily tier migrations, weekly price shifts, and late-arriving refunds using a seeded pseudo-clock simulator.
- **Defensive Chaos Testing**: Proves data reliability through automated injection of 6 edge-case data corruption scenarios (retroactive price edits, duplicate writes, late refunds, orphan orders, overpayments, and pipeline skips).
- **Asset-Centric Orchestration**: Models every dbt model and snapshot as a Dagster software-defined asset with built-in asset checks and automated reconciliation.
- **Automated Lineage & Documentation**: dbt documentation, schema contracts, and interactive DAG lineage published automatically via GitHub Pages.

---

## Architectural Setup

All warehouse layers reside within a single DuckDB database, enforcing strict unidirectional data flow where downstream layers read only from their immediate upstream contracts.

```text
+-------------------------------------------------------------------------+
|                        Dagster Orchestrator                             |
|          (Asset-based orchestration, daily schedules & checks)          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+------------------+     +--------------------+     +---------------------+
| Python Simulator | --> |   DuckDB (raw)     | --> |   dbt Staging       |
| (Seeded events)  |     | (Shops, Customers, |     | (Views: 1-to-1 with |
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

### Layer Contracts

1. **`raw` (DuckDB schema `raw`)**: Raw tables populated exclusively by the Python simulator (`simulator/loader.py`). Stamped with ingestion metadata (`_loaded_at`). dbt never writes to `raw`.
2. **`staging` (DuckDB views)**: 1-to-1 mappings with raw tables. Responsible solely for column renaming, datatype casting, and whitespace trimming. No joins or business logic.
3. **`snapshots` (DuckDB tables)**: dbt snapshots using the `timestamp` strategy on `updated_at`. Tracks historical versions for customer loyalty tiers (`snap_customers`) and product prices (`snap_products`).
4. **`core` (DuckDB tables)**: Star schema dimensional models and incremental fact tables:
   - `dim_shops`: Type 1 physical store dimension.
   - `dim_customers`: SCD Type 2 customer dimension with surrogate keys.
   - `dim_products`: SCD Type 2 product dimension with surrogate keys.
   - `dim_date`: Generated calendar date spine.
   - `fct_order_items`: Incremental sales fact joining point-in-time dimensions via `as_of_join`.
   - `fct_refunds`: Incremental refunds fact with 7-day lookback window.
5. **`marts` (DuckDB tables)**: Curated analytical reporting tables:
   - `mrt_daily_sales`: Daily net revenue by store, reconciled against refunds.
   - `mrt_product_perf`: Product sales velocity and price elasticity.
   - `mrt_tier_moves`: Customer loyalty tier transitions and longitudinal spending behavior.

### Star Schema & Data Grain

| Entity | Grain | Primary / Surrogate Key | Dimension Type |
|---|---|---|---|
| `dim_customers` | One row per customer loyalty tier version | `customer_sk` | SCD Type 2 |
| `dim_products` | One row per product unit price version | `product_sk` | SCD Type 2 |
| `dim_shops` | One row per physical retail shop | `shop_sk` | Type 1 |
| `dim_date` | One row per calendar day | `date_key` | Date spine |
| `fct_order_items` | One row per sale line item | `order_item_id` | Incremental Fact (`delete+insert`) |
| `fct_refunds` | One row per returned item line | `refund_id` | Incremental Fact (`delete+insert`) |

### Point-in-Time SCD2 As-Of Join

The point-in-time join logic is defined in `dbt/macros/as_of_join.sql` and utilized by `fct_order_items`:

```sql
select
    oi.order_item_id,
    c.customer_sk,
    p.product_sk,
    oi.quantity,
    oi.quantity * p.unit_price_kes - oi.discount_kes as line_amount_kes
from {{ ref('stg_order_items') }} oi
join {{ ref('stg_orders') }} o using (order_id)
left join {{ ref('dim_customers') }} c
    on c.customer_id = o.customer_id
   and o.order_ts >= c.valid_from
   and o.order_ts <  coalesce(c.valid_to, timestamp '9999-12-31')
left join {{ ref('dim_products') }} p
    on p.product_id = oi.product_id
   and o.order_ts >= p.valid_from
   and o.order_ts <  coalesce(p.valid_to, timestamp '9999-12-31')
```

`LEFT JOIN` semantics ensure that missing or non-contiguous dimension records produce `NULL` surrogate keys, prompting an immediate `not_null` schema test failure rather than silently dropping orphan orders.

---

## Repository Structure

```text
dukastack/
├── README.md                    # Project overview, features, architecture, and repo structure
├── Makefile                     # Developer commands (setup, demo, build, chaos, docs, dagster, lint, test)
├── pyproject.toml               # Pinned Python package dependencies and tool configurations
├── .sqlfluff                    # SQLFluff linter settings for DuckDB dialect and dbt templating
├── .pre-commit-config.yaml      # Git pre-commit hooks for formatting and linting
├── .gitignore                   # Local data files and dbt build target exclusions
├── .github/
│   └── workflows/
│       ├── ci.yml               # PR validation: linting, pytest, seeded dbt build, idempotency, chaos suite
│       └── docs.yml             # Main branch deployment of dbt docs to GitHub Pages
├── docs/
│   ├── requirements.md          # Full project functional and non-functional specifications
│   ├── architecture.md          # Deep dive into layers, contracts, and technology decisions
│   ├── chaos-scenarios.md       # Detailed guide to injected chaos scenarios C1-C6
│   ├── adr/                     # Architectural Decision Records
│   │   ├── 0001-duckdb-over-postgres.md
│   │   ├── 0002-timestamp-snapshot-strategy.md
│   │   ├── 0003-refunds-as-separate-fact.md
│   │   └── 0004-retroactive-price-changes.md
│   └── queries/
│       └── price_and_tier_at_sale.sql  # Saved query demonstrating historical price/tier reconstruction
├── simulator/                   # Synthetic retail POS generator and chaos injector
│   ├── cli.py                   # Simulator CLI: generate, advance, chaos
│   ├── config.py                # Simulation seed, shops catalog, product catalog, daily rates
│   ├── generate.py              # Baseline historical data generation
│   ├── mutate.py                # Daily progression: tier updates, price changes, orders, refunds
│   ├── chaos.py                 # Scenarios C1 to C6 corruption injectors
│   └── loader.py                # Ingestion into DuckDB raw schema with _loaded_at stamps
├── dbt/                         # dbt transformation project
│   ├── dbt_project.yml          # dbt project definition and model materializations
│   ├── profiles.yml             # DuckDB connection profile via environment variable
│   ├── packages.yml             # External dbt packages (dbt_utils, dbt_expectations, dbt_project_evaluator)
│   ├── models/
│   │   ├── sources.yml          # Raw table definitions and freshness thresholds
│   │   ├── staging/             # 1-to-1 views on raw tables (stg_shops, stg_customers, stg_orders, etc.)
│   │   ├── core/                # Star schema: dim_*, fct_order_items, fct_refunds, boundary unit tests
│   │   └── marts/               # Business reporting marts (mrt_daily_sales, mrt_product_perf, mrt_tier_moves)
│   ├── snapshots/               # SCD Type 2 snapshot definitions (snap_customers, snap_products)
│   ├── macros/                  # Custom SQL macros (as_of_join.sql)
│   └── tests/singular/          # Business logic and reconciliation tests (assert_scd2_no_overlap, etc.)
├── orchestration/               # Dagster asset definitions and orchestration pipelines
│   └── dukastack_dagster/
│       ├── definitions.py       # Dagster definitions entry point
│       ├── assets.py            # Software-defined assets for simulator and dbt models
│       ├── checks.py            # Row count reconciliation and snapshot freshness checks
│       └── schedules.py         # Daily automated pipeline schedule
├── tests/                       # Python test suite
│   ├── test_determinism.py      # Verifies simulator output reproducibility under fixed seeds
│   └── test_chaos.py            # Verifies that each chaos scenario is caught by its intended test
└── data/                        # Local DuckDB database and simulator state (gitignored)
```

---

## Defensive Chaos Scenarios

Every test in dukastack exists because a failure mode justified it. The simulator can inject 6 distinct failure modes to verify that automated checks catch data issues before they reach production marts:

| ID | Scenario | Injection Mechanism | Caught By | Severity |
|---|---|---|---|---|
| **C1** | Retroactive price correction | Changes price but back-dates `updated_at` before last snapshot | `assert_snapshot_matches_source` | error |
| **C2** | Late-arriving refund | Writes refund today for order placed 5 days ago | 7-day incremental lookback; verified by `assert_daily_sales_reconcile` | error |
| **C3** | Orphan order | Generates order for non-existent `customer_id` | `not_null` & `relationships` on `fct_order_items.customer_sk` | error |
| **C4** | Duplicate customer row | Duplicate row with matching `customer_id` and `updated_at` | `unique` test on `stg_customers.customer_id` | error |
| **C5** | Overpaid order | Payments total exceeds line items sum | `assert_payments_within_order_total` | error |
| **C6** | Skipped day | Advances 2 days with same customer changing tier on both | Dagster freshness check on `snap_customers` | warn |

---

## License

This project is licensed under the [MIT License](LICENSE).
