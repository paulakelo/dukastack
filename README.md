# dukastack 

[![CI](https://github.com/paulakelo/dukastack/actions/workflows/ci.yml/badge.svg)](https://github.com/paulakelo/dukastack/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/dbt--docs-GitHub%20Pages-blue)](https://paulakelo.github.io/dukastack/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0+-yellow.svg)](https://duckdb.org/)
[![dbt](https://img.shields.io/badge/dbt-1.8+-FF694B.svg)](https://www.getdbt.com/)
[![Dagster](https://img.shields.io/badge/Dagster-1.8+-2563EB.svg)](https://dagster.io/)

A local, zero-cost analytics warehouse for point-of-sale data from a fictional chain of Kenyan *duka* (small retail shops), built with **dbt**, **DuckDB**, and **Dagster**.


---

## The Problem dukastack Solves

Legacy retail POS systems record *what* was sold, but frequently fail to record *what unit price* or *what customer loyalty tier* applied at the exact second the sale completed.

dukastack reconstructs historical truth using point-in-time as-of joins against SCD Type 2 dimensions:
- *"What price applied when this sale happened?"*
- *"Which loyalty tier was active at order timestamp?"*
- *"Did units sold shift following the price change?"*

Every answer is deterministic, idempotent, and backed by a comprehensive automated test suite.

---

## Architecture at a Glance

All storage layers live in a single embedded DuckDB file (`data/dukastack.duckdb`), eliminating cloud infrastructure costs while running identically on a developer laptop and in GitHub Actions CI.

```
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

### Star Schema & Data Grain

| Entity | Grain | Key | Type |
|---|---|---|---|
| `dim_customers` | One row per customer loyalty version | `customer_sk` | SCD Type 2 |
| `dim_products` | One row per product price version | `product_sk` | SCD Type 2 |
| `dim_shops` | One row per physical retail store | `shop_sk` | Type 1 |
| `dim_date` | One row per calendar day | `date_key` | Date spine |
| `fct_order_items` | One row per sale line item | `order_item_id` | Incremental Fact |
| `fct_refunds` | One row per item return | `refund_id` | Incremental Fact |

---

## What We Broke on Purpose (Chaos Scenarios)

Every test in dukastack exists because a failure justified it. The `chaos` simulator injects scenarios C1 through C6 into a copy of the database to prove test coverage:

| ID | Scenario | Injection Mechanism | Caught By | Severity |
|---|---|---|---|---|
| **C1** | Retroactive price correction | Changes price but back-dates `updated_at` before last snapshot | `assert_snapshot_matches_source` | error |
| **C2** | Late-arriving refund | Writes refund today for order placed 5 days ago | 7-day incremental lookback; verified by `assert_daily_sales_reconcile` | error |
| **C3** | Orphan order | Generates order for non-existent `customer_id` | `not_null` & `relationships` on `fct_order_items.customer_sk` | error |
| **C4** | Duplicate customer row | Duplicate row with matching `customer_id` and `updated_at` | `unique` test on `stg_customers.customer_id` | error |
| **C5** | Overpaid order | Payments total exceeds line items sum | `assert_payments_within_order_total` | error |
| **C6** | Skipped day | Advances 2 days with same customer changing tier on both | Dagster freshness check on `snap_customers` | warn |

---

## Quickstart

Clone to green in five commands:

```bash
# 1. Clone repository
git clone https://github.com/paulakelo/dukastack.git
cd dukastack

# 2. Setup virtual environment & dependencies
make setup
source .venv/bin/activate

# 3. Generate initial POS history and run demo pipeline
make demo

# 4. Run dbt build (snapshots, models, singular & generic tests)
make build

# 5. Execute chaos testing suite
make chaos
```

### Available Make Targets

- `make setup` - Create virtualenv and install pinned dependencies.
- `make demo` - Generate history, then advance 14 days with dbt builds after each day.
- `make build` - Run `dbt build` (snapshots, models, tests).
- `make chaos` - Inject chaos scenarios C1 to C6 and run tests.
- `make docs` - Generate and serve dbt interactive documentation.
- `make dagster` - Start the Dagster UI webserver.
- `make lint` - Lint Python (`ruff`) and SQL (`sqlfluff`).
- `make test` - Run Python tests (`pytest`).

---

## Point-in-Time SCD2 As-Of Join

The point-in-time join is defined once in `dbt/macros/as_of_join.sql`:

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

`LEFT JOIN` is deliberate: missing dimension records yield `NULL` surrogate keys, failing the `not_null` schema test immediately rather than masking data anomalies.

---

## Milestones

- [ ] **M1: Simulator & Raw Load** - Deterministic synthetic generation, DuckDB loading.
- [ ] **M2: Staging & Freshness** - 7 staging views, source freshness, schema validation.
- [ ] **M3: Snapshots** - SCD Type 2 tracking for loyalty tiers and unit prices.
- [ ] **M4: Core Star Schema** - Dimensions, fact tables, as-of joins, and boundary unit tests.
- [ ] **M5: Incremental Facts & Marts** - Lookback incremental logic, 3 marts, reconciliation tests.
- [ ] **M6: Orchestration, CI & Docs** - Dagster assets/checks, CI pipeline, published lineage docs.

---

## License

MIT License. 
