# dukastack: Requirements, Architecture and Repo Plan

Oct 14, 2026 · @Paul Grant

## Overview

dukastack is a local, zero-cost analytics warehouse for point-of-sale data from a fictional chain of Kenyan duka (small retail shops), built with dbt, DuckDB and Dagster. It exists to prove one skill most portfolios fake: slowly changing dimensions that stay correct when prices and loyalty tiers change.

The legacy POS records what was sold, but not at what price or for which loyalty tier. The warehouse reconstructs both for every sale, so "what price and tier applied when this sale happened?" has one tested answer.

**Goals**

1. Correct point-in-time history for customer tier and product price (SCD Type 2).
2. Every model tested, including the edge cases of the point-in-time join and deliberately injected data problems.
3. Clone to green in five commands, with a fixed seed so every run produces identical data.
4. Lineage, model docs and test results published as a public link.

**Non-goals for v1:** cloud warehouses, BI dashboards beyond one screenshot, streaming ingestion, multiple source systems.

## Users and personas

Five kinds of readers use the warehouse, and each one maps to a question it must answer correctly.

| Persona | Needs | Question the warehouse must answer |
| --- | --- | --- |
| Finance analyst | Revenue they can trust, net of refunds | What was net revenue per shop per day last month? |
| Merchandising manager | The effect of price changes on sales | How did units sold move after a price change, by category? |
| Loyalty manager | Customer movement between tiers (basic, silver, gold) | How many customers moved from basic to silver this month, and what did they spend before and after? |
| Data engineer (the maintainer) | Safe changes and fast failures | Which test failed, on which rows, and why? |
| Hiring reviewer | Evidence in under five minutes | Does the repo show tested SCD2, CI, docs and orchestration? |

## Functional requirements

Fifteen requirements define "done"; each has an acceptance criterion you can check with a command or a test.

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | The simulator generates N days of shop history from a seed. | The same seed produces identical raw tables (a pytest hash test). |
| FR-02 | The simulator advances the source by one simulated day on demand. | `advance` adds that day's orders and refunds and applies price and tier changes, each stamped with `updated_at`. |
| FR-03 | Raw tables load into DuckDB schema `raw` unchanged, plus `_loaded_at`. | Row counts in `raw` equal simulator output; dbt never writes to `raw`. |
| FR-04 | One staging model per raw table that only renames, casts and trims. | No joins in `stg_*`; each has `unique` and `not_null` on its key. |
| FR-05 | Snapshots track customer loyalty tier and product unit price. | A customer whose tier changed twice has 3 contiguous versions: each `dbt_valid_to` equals the next `dbt_valid_from`. |
| FR-06 | `dim_customers` and `dim_products` are SCD2 with surrogate keys; `dim_shops` is Type 1; `dim_date` is a date spine. | Surrogate keys are unique, at most one current row per natural key, and validity ranges never overlap. |
| FR-07 | `fct_order_items` has one row per order line, is incremental, and carries as-of dimension keys. | Customer and product keys are the versions valid at `order_ts`; boundary cases are covered by unit tests. |
| FR-08 | Refunds are a separate fact, `fct_refunds`; sales rows are never edited or deleted. | Sale rows are unchanged after a refund; a refund never exceeds its line amount. |
| FR-09 | Three marts: `mrt_daily_sales`, `mrt_product_perf`, `mrt_tier_moves`. | Marts read only from core models; net revenue in `mrt_daily_sales` reconciles to the facts. |
| FR-10 | A saved query returns the price and tier in force for any sale. | `docs/queries/price_and_tier_at_sale.sql` returns the right values for a known sample order. |
| FR-11 | Source freshness is declared on every `raw` table. | Warn after 1 day without new `_loaded_at`, error after 3. |
| FR-12 | `dbt build` is the single entry point: snapshots, models and tests in DAG order. | A failing test stops downstream models and returns a non-zero exit code. |
| FR-13 | Dagster exposes every dbt model as an asset, with asset checks and a daily schedule. | The schedule runs `advance` then `dbt build`; a failed check shows in the Dagster UI. |
| FR-14 | CI runs lint and `dbt build` on every pull request; docs publish from `main`. | A failing test blocks the PR; the docs URL is in the README. |
| FR-15 | A `chaos` command injects scenarios C1 to C6 (see Source system and simulator). | Each scenario fails its named test (see Testing and data quality). |

## Non-functional requirements

The project must cost nothing, run on a laptop, and behave the same way every time. The numeric targets below are proposals; adjust them once you measure.

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-01 | Cost | $0: no paid services; runs on a laptop and free CI minutes. |
| NFR-02 | Reproducibility | Pinned dependencies and a seeded simulator; five commands from clone to a green build. |
| NFR-03 | Demo scale | 5 shops, about 500 orders a day, 90 simulated days. |
| NFR-04 | Performance | Full build under 2 minutes and a one-day incremental build under 20 seconds, on a laptop at demo scale. |
| NFR-05 | Idempotency | A second `dbt build` with no new data changes no rows (checked in CI). |
| NFR-06 | Documentation | Every model has a description and every key column is described; CI fails on gaps (`dbt_project_evaluator`). |
| NFR-07 | Style | `sqlfluff` (DuckDB dialect) and `ruff` pass in CI; naming follows the conventions in Repository structure. |
| NFR-08 | Data safety | Synthetic data only: no real names or phone numbers, and no secrets in the repo. |
| NFR-09 | Decisions | One short ADR for every decision that had a real alternative. |

## Source system and simulator

The source is a Python simulator that mutates a simulated POS database one day at a time; static CSVs cannot produce SCD2 history because they never change. Time is a simulated clock, not wall-clock time, and every rate lives in `simulator/config.py`.

**Raw tables** (schema `raw`, amounts in KES)

| Table | Columns | How it changes |
| --- | --- | --- |
| `shops` | `shop_id`, `shop_name`, `county`, `updated_at` | Static. |
| `customers` | `customer_id`, `customer_name` (synthetic), `county`, `loyalty_tier` (basic, silver, gold), `updated_at` | A configurable share of customers change tier each day. |
| `products` | `product_id`, `product_name`, `category`, `unit_price_kes`, `updated_at` | A configurable share of products change price each week. |
| `orders` | `order_id`, `shop_id`, `customer_id`, `order_ts`, `order_status`, `updated_at` | New orders daily; status moves from placed to completed. |
| `order_items` | `order_item_id`, `order_id`, `product_id`, `quantity`, `discount_kes`, `updated_at` | New with orders. It has no price column on purpose: the legacy POS never stored one. |
| `payments` | `payment_id`, `order_id`, `method` (cash, mpesa, card), `amount_kes`, `paid_at`, `updated_at` | One or more per order. |
| `refunds` | `refund_id`, `order_item_id`, `quantity`, `refund_kes`, `refunded_at`, `updated_at` | Arrive up to 7 days after the sale. |

**What `advance` does for one simulated day**

1. Create the day's orders, order items and payments.
2. Move yesterday's placed orders to completed.
3. Change the loyalty tier of a share of customers.
4. Change the unit price of a share of products.
5. Create refunds against orders up to 7 days old.
6. Stamp every touched row with `updated_at` from the simulated clock.

**Chaos scenarios** (`chaos` command; the test that catches each one is listed under Testing and data quality)

| ID | Scenario | How the simulator injects it |
| --- | --- | --- |
| C1 | Retroactive price correction | Changes a product's price but back-dates `updated_at` to before the last snapshot. |
| C2 | Late-arriving refund | Writes a refund today for an order placed 5 days ago. |
| C3 | Orphan order | Creates an order whose `customer_id` is not in `customers`. |
| C4 | Duplicate customer row | Inserts a second row with the same `customer_id` and `updated_at`. |
| C5 | Overpaid order | Writes payments that total more than the order's items. |
| C6 | Skipped day | Advances two days between builds, with the same customer changing tier on both. |

## Architecture

One DuckDB file holds every layer, so the whole system runs on a laptop and in free CI.

&#91;embedded content: system context · five layers in one DuckDB file, run by Dagster, tested by CI\]

The simulator writes `raw`; dbt builds staging, snapshots, core and marts in that order; Dagster schedules the sequence and GitHub Actions tests it on every pull request.

**Technology choices**

| Choice | Why | Rejected alternative |
| --- | --- | --- |
| DuckDB | One file, no server, free in CI, fast on analytics queries. | Postgres: needs a running service. |
| dbt-core with `dbt-duckdb` | Full dbt features (tests, snapshots, unit tests, docs) at no cost. | dbt Cloud: paid, hides the CLI workflow. |
| Python simulator | The only way to get real change history for SCD2. | Static CSV seeds: they never change, so SCD2 would be decorative. |
| Dagster | Assets map one-to-one to dbt models; installs with pip. | Airflow: heavy to run locally and distracts from dbt. |
| GitHub Actions and Pages | Free CI and a public docs link. | Self-hosted CI: extra infrastructure. |

## Data flow and layering

Data moves one way, from raw to marts, and each layer has a single job that tests can enforce.

&#91;embedded content: layer contracts · five layers, what each holds and what it may read\]

A layer may read only from the layer named on its arrow; `dbt_project_evaluator` fails CI when a model breaks that rule.

**Flow rules**

1. Only `simulator/loader.py` writes `raw`.
2. Staging models are views; core and marts are tables.
3. Both facts are incremental with `delete+insert` and a 7-day lookback on `updated_at`, which is what absorbs late-arriving refunds (C2).
4. Snapshots run inside `dbt build`, so tests always see fresh history.
5. Lineage is generated by `dbt docs` and published to GitHub Pages.

## Data model

One fact table and four dimensions form the star; the two SCD2 dimensions give every sale the customer tier and product price that were true when it happened.

&#91;embedded content: star schema · one fact, four dimensions, two of them SCD2\]

The as-of join is defined once, in `macros/as_of_join.sql`, and used by `fct_order_items`:

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

The joins are left joins on purpose: an order with no matching version gets a null key, and the `not_null` test on `fct_order_items` fails loudly instead of hiding the orphan (C3).

**Grain and keys**

| Table | Grain | Key | Type |
| --- | --- | --- | --- |
| `dim_customers` | One row per customer version | `customer_sk` | SCD2 |
| `dim_products` | One row per product version | `product_sk` | SCD2 |
| `dim_shops` | One row per shop | `shop_sk` | Type 1 |
| `dim_date` | One row per calendar day | `date_key` | Date spine |
| `fct_order_items` | One row per order line | `order_item_id` | Incremental fact |
| `fct_refunds` | One row per refund, pointing at its order line | `refund_id` | Incremental fact |

Surrogate keys come from `dbt_utils.generate_surrogate_key` over the natural key and `valid_from`, so a new version always gets a new key.

## Repository structure

Four top-level code folders map to four jobs: `simulator/` makes data, `dbt/` transforms it, `orchestration/` schedules it, and `tests/` checks the Python side.

```text
dukastack/
├── README.md                    # quickstart, architecture, "what I broke on purpose"
├── Makefile                     # setup, demo, build, chaos, docs, dagster, lint, test
├── pyproject.toml               # pinned: dbt-core, dbt-duckdb, dagster, dagster-dbt, ruff, sqlfluff, pytest
├── .sqlfluff
├── .pre-commit-config.yaml
├── .gitignore                   # ignores data/ and dbt/target/
├── .github/
│   └── workflows/
│       ├── ci.yml               # pull request: lint, simulator tests, seeded dbt build, second build (idempotency)
│       └── docs.yml             # main: dbt docs generate, publish to GitHub Pages
├── docs/
│   ├── requirements.md          # this document, exported
│   ├── architecture.md
│   ├── chaos-scenarios.md       # C1 to C6: what breaks, which test catches it
│   ├── adr/
│   │   ├── 0001-duckdb-over-postgres.md
│   │   ├── 0002-timestamp-snapshot-strategy.md
│   │   ├── 0003-refunds-as-separate-fact.md
│   │   └── 0004-retroactive-price-changes.md
│   └── queries/
│       └── price_and_tier_at_sale.sql
├── simulator/
│   ├── cli.py                   # generate | advance | chaos
│   ├── config.py                # seed, shops, products, daily rates
│   ├── generate.py              # initial history
│   ├── mutate.py                # daily price and tier changes, refunds
│   ├── chaos.py                 # scenarios C1 to C6
│   └── loader.py                # writes raw.* into DuckDB with _loaded_at
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml             # DuckDB path from an env var; no secrets
│   ├── packages.yml             # dbt_utils, dbt_expectations, dbt_project_evaluator
│   ├── models/
│   │   ├── sources.yml          # raw tables + freshness
│   │   ├── staging/             # stg_shops, stg_customers, stg_products, stg_orders,
│   │   │   │                    # stg_order_items, stg_payments, stg_refunds
│   │   │   └── _stg__models.yml
│   │   ├── core/                # dim_shops, dim_customers, dim_products, dim_date,
│   │   │   │                    # fct_order_items, fct_refunds
│   │   │   ├── _core__models.yml
│   │   │   └── _core__unit_tests.yml
│   │   └── marts/               # mrt_daily_sales, mrt_product_perf, mrt_tier_moves
│   │       └── _marts__models.yml
│   ├── snapshots/
│   │   ├── snap_customers.sql   # tracks loyalty_tier
│   │   └── snap_products.sql    # tracks unit_price_kes
│   ├── macros/
│   │   └── as_of_join.sql       # the point-in-time join, defined once
│   └── tests/
│       └── singular/
│           ├── assert_scd2_no_overlap.sql
│           ├── assert_snapshot_matches_source.sql
│           ├── assert_payments_within_order_total.sql
│           └── assert_daily_sales_reconcile.sql
├── orchestration/
│   └── dukastack_dagster/
│       ├── definitions.py
│       ├── assets.py            # dbt models as assets, plus the simulator step
│       ├── checks.py            # row-count reconciliation, freshness
│       └── schedules.py         # daily: advance, then dbt build
├── tests/                       # Python tests for the simulator
│   ├── test_determinism.py
│   └── test_chaos.py
└── data/                        # gitignored: dukastack.duckdb, simulator state
```

**Conventions**

| Thing | Rule | Example |
| --- | --- | --- |
| Model prefix | `stg_`, `snap_`, `dim_`, `fct_`, `mrt_` | `fct_order_items` |
| Surrogate key | `<entity>_sk`; natural key keeps `<entity>_id` | `customer_sk`, `customer_id` |
| Timestamps and dates | `_ts` for timestamps, `_date` for dates | `order_ts`, `order_date` |
| Money | KES, suffix `_kes` | `refund_kes` |
| Booleans | `is_` prefix | `is_current` |
| YAML files | One per folder, prefixed with an underscore | `_core__models.yml` |
| Branches and commits | Branch per milestone; commit messages in the imperative | `Add as-of join macro` |

**Make targets**

| Target | Does |
| --- | --- |
| `make setup` | Create the virtualenv and install pinned dependencies. |
| `make demo` | Generate history, then advance 14 days with a `dbt build` after each day. |
| `make build` | Run `dbt build`. |
| `make chaos` | Inject C1 to C6 into a copy of the database and run the tests. |
| `make docs` | Generate and serve the dbt docs. |
| `make dagster` | Start the Dagster UI. |
| `make lint` and `make test` | Run `sqlfluff` and `ruff`, then `pytest`. |

## Testing and data quality

Every chaos scenario must fail a named test, and every test must exist because some failure justified it. Six layers of checks run in order from cheapest to most expensive.

| Layer | What it checks | Tool |
| --- | --- | --- |
| Python tests | Simulator is deterministic; each chaos injector breaks what it claims to break. | `pytest` |
| Source freshness | `raw` tables received data recently (`_loaded_at`). | dbt `source freshness` |
| Generic tests | `unique`, `not_null`, `relationships` on surrogate keys, `accepted_values` for tier, status and payment method. | dbt schema YAML |
| Singular tests | SCD2 ranges never overlap; snapshot matches source; payments within order total; marts reconcile to facts. | SQL in `dbt/tests/singular/` |
| Unit tests | As-of join at its boundaries; line amount with discount; refund sign. | dbt unit tests (dbt 1.8+) |
| Asset checks | Row counts reconcile between `raw` and `stg_*`; snapshot freshness. | Dagster |

**As-of join cases the unit tests must cover**

1. An order exactly at `valid_from` gets the new version.
2. An order one second before `valid_to` gets the old version.
3. An order after the last version gets the current version.
4. An order before the first version gets no match, so the fact's `not_null` test fails loudly.

**Which test catches which chaos scenario**

| ID | Scenario | Caught by | Severity |
| --- | --- | --- | --- |
| C1 | Retroactive price correction | `assert_snapshot_matches_source`: the current snapshot row differs from the source row. | error |
| C2 | Late-arriving refund | Incremental lookback picks it up; `assert_daily_sales_reconcile` proves the mart still matches the facts. | error |
| C3 | Orphan order | `not_null` and `relationships` on `fct_order_items.customer_sk`. | error |
| C4 | Duplicate customer row | `unique` on `stg_customers.customer_id`, before the snapshot runs. | error |
| C5 | Overpaid order | `assert_payments_within_order_total`. | error |
| C6 | Skipped day | Dagster freshness check on `snap_customers`; the lost intermediate version is a documented limit (ADR-0002). | warn |

## CI/CD and orchestration

GitHub Actions proves every change on a seeded database, and Dagster runs the same sequence on a daily schedule.

**Pull request pipeline (`ci.yml`)**

1. Install pinned dependencies.
2. Run `ruff`, `sqlfluff` and `pytest`.
3. Generate 30 days of history with the fixed seed, then advance 3 days.
4. Run `dbt build`; any failing test fails the job.
5. Run `dbt build` a second time and assert that nothing changed (idempotency).
6. Run `make chaos` and assert that each scenario fails its named test.

**Publish pipeline (`docs.yml`, on merge to `main`)**

1. Run `dbt docs generate`.
2. Publish the site to GitHub Pages, so the lineage graph is a public link in the README and on a resume.

**Dagster**

| Piece | Behavior |
| --- | --- |
| Assets | `dagster-dbt` turns every dbt model, snapshot and seed into an asset, so lineage appears in two places. |
| Simulator asset | Runs `advance` and loads `raw`; every dbt asset depends on it. |
| Asset checks | Row-count reconciliation between `raw` and `stg_*`; freshness on `snap_*`. |
| Schedule | Daily: `advance`, then `dbt build`. |
| Sensors | None in v1. |

## Milestones, risks and scope

Build in six milestones, one branch each; a milestone is done only when its proof exists in the repo.

| # | Milestone | Definition of done | Proof |
| --- | --- | --- | --- |
| M1 | Simulator and raw load | `generate` and `advance` work; same seed gives identical tables; `raw` loads into DuckDB. | `pytest` determinism test passes. |
| M2 | Staging and tests | Seven `stg_*` models with `unique` and `not_null` tests; source freshness declared. | `dbt build` green on 7 days of history. |
| M3 | Snapshots | Both snapshots run daily; one customer shows 3 tier versions with contiguous ranges. | Query output saved in `docs/`. |
| M4 | Core star schema | Dimensions and `fct_order_items` with the as-of join; unit tests on all four boundary cases. | `docs/queries/price_and_tier_at_sale.sql` returns correct values. |
| M5 | Incremental facts and marts | `fct_order_items` incremental; `fct_refunds`; three marts; reconciliation test. | Second `dbt build` changes nothing. |
| M6 | Orchestration, CI, docs | Dagster assets and checks; CI with the chaos job; docs on GitHub Pages; README with the "what I broke on purpose" table. | Public docs link and a green CI badge. |

**Risks**

| Risk | Mitigation |
| --- | --- |
| Timestamp snapshots miss back-dated changes (C1). | Detect with `assert_snapshot_matches_source`; record the trade-off in ADR-0004. |
| A skipped day loses an intermediate tier version (C6). | Daily schedule plus a freshness check; accept and document the limit. |
| Scope creep into BI or cloud. | Out-of-scope list below; one dashboard screenshot at most. |
| Dagster and dbt version drift. | Pin versions in `pyproject.toml`; upgrade in a dedicated PR. |

**Out of scope for v1:** cloud warehouses, Kubernetes, streaming ingestion, multiple source systems, a full BI dashboard, and real customer data.
