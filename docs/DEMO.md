# DukaStack 2-Minute Demo Recording Runbook

This runbook guides a crisp, 2-to-3 minute video demonstration of **dukastack**:
a zero-cost, local retail analytics warehouse built with **dbt**, **DuckDB**, and **Dagster** over synthetic Kenyan duka point-of-sale (POS) data.

---

## Overview of Demo Beats

| Beat | Action / Command | UI View | One-Sentence Spoken Script | Target Duration |
| :--- | :--- | :--- | :--- | :--- |
| **1. Intro & Demo Setup** | `make demo` | Terminal | *"We start with a clean local environment, generate 30 days of synthetic Kenyan retail transactions, and build our complete dbt warehouse in DuckDB."* | 0:00 - 0:25 |
| **2. dbt Docs & Lineage** | `make docs-serve` | Browser (`http://localhost:8080`) | *"In the dbt documentation, our lineage graph reveals the data journey from raw POS ingestion through SCD Type 2 snapshots, star-schema core dimensions, and contract-enforced marts."* | 0:25 - 0:50 |
| **3. Dagster Asset Graph** | `make dagster` | Browser (`http://localhost:3000`) | *"Dagster models our entire data warehouse as software-defined assets, coupling dbt transformations directly with asset checks and automated sensors."* | 0:50 - 1:15 |
| **4. Inject Fault** | `make demo-fail` | Terminal | *"To test our data contracts and quality gates, we simulate a POS glitch by injecting duplicate order item line transactions."* | 1:15 - 1:35 |
| **5. Observe Blocked Marts**| Refresh Dagster UI / inspect test | Browser & Terminal | *"Dagster and dbt immediately flag the uniqueness test violation on `stg_order_items`, halting execution and preventing corrupted data from reaching downstream marts."* | 1:35 - 1:55 |
| **6. Automated Recovery** | `make demo-recover` | Terminal & Browser | *"Once the offending batch is purged, our recovery run restores the pipeline to a 100% green passing state."* | 1:55 - 2:15 |
| **7. SCD2 Point-in-Time Proof** | `make queries` | Terminal & `docs/sample_queries.md` | *"Finally, querying our product performance mart demonstrates SCD Type 2 correctness, proving that price changes preserve exact historical revenues without retroactive distortion."* | 2:15 - 2:45 |

---

## Step-by-Step Execution Guide

### Beat 1: Initialize Demo Warehouse

**Terminal Command:**

```bash
make demo
```

**What happens:**

- Cleans any previous database artifacts in `data/`.
- Runs `simulator.cli generate --days 30 --seed 42` to create synthetic Kenyan POS records (shops, products, customers, orders, order items, payments, refunds).
- Executes `dbt build` (snapshots, staging models, core dimensions, incremental facts, contracts, and tests).

**Spoken Script:**
> *"We start with a clean local environment, generate 30 days of synthetic Kenyan retail transactions, and build our complete dbt warehouse in DuckDB."*

---

### Beat 2: Explore dbt Documentation & Lineage

**Terminal Command (in a separate tab or background):**

```bash
make docs-serve
```

**Browser Navigation:**

- Open `http://localhost:8080`.
- Click the bottom-right **Lineage Graph** icon.
- Filter to a mart (e.g., `mrt_daily_sales` or `mrt_product_perf`).
- Point out the **Exposures** tab showing business questions BQ-1 through BQ-5.
- Open `mrt_product_perf` model details to showcase the explicit **GRAIN** definition and contract enforcement.

**Spoken Script:**
> *"In the dbt documentation, our lineage graph reveals the data journey from raw POS ingestion through SCD Type 2 snapshots, star-schema core dimensions, and contract-enforced marts."*

---

### Beat 3: Inspect Dagster Asset Graph

**Terminal Command (in a separate tab):**

```bash
make dagster
```

**Browser Navigation:**

- Open `http://localhost:3000`.
- Navigate to **Deployment** -> **Assets** (or **Asset Groups**).
- Show the visual flow from `raw_pos_data` asset through `snapshots`, `staging`, `core`, and `marts`.
- Highlight the real-time **Asset Checks** attached to each model.

**Spoken Script:**
> *"Dagster models our entire data warehouse as software-defined assets, coupling dbt transformations directly with asset checks and automated sensors."*

---

### Beat 4: Inject Chaos (Data Quality Failure)

**Terminal Command:**

```bash
make demo-fail
```

**What happens:**

- Injects a duplicate sales line item (`ITM-00000001`) into the raw POS data stream.
- Executes `dbt build --select stg_order_items+`.

**Spoken Script:**
> *"To test our data contracts and quality gates, we simulate a POS glitch by injecting duplicate order item line transactions."*

---

### Beat 5: Demonstrate Pipeline Circuit Breaker

**In Browser / Terminal:**

- Show the dbt test error output: `unique_stg_order_items_order_item_id FAIL [1 error]`.
- Point out that downstream models `fct_order_items`, `fct_refunds`, `mrt_daily_sales`, and `mrt_product_perf` are **SKIP [not run]**.
- If viewing in Dagster UI, show the red failed asset check and blocked downstream assets.

**Spoken Script:**
> *"Dagster and dbt immediately flag the uniqueness test violation on `stg_order_items`, halting execution and preventing corrupted data from reaching downstream marts."*

---

### Beat 6: Recover to Green

**Terminal Command:**

```bash
make demo-recover
```

**What happens:**

- Deletes the duplicate row from `raw.order_items`.
- Re-runs `dbt build --select stg_order_items+`.
- All tests pass: `PASS=20 WARN=0 ERROR=0 SKIP=0`.

**Spoken Script:**
> *"Once the offending batch is purged, our recovery run restores the pipeline to a 100% green passing state."*

---

### Beat 7: Run Sample Queries & Prove SCD2 Correctness

**Terminal Command:**

```bash
make queries
```

**What to show:**

- Open `docs/sample_queries.md` or display the output of `queries/bq3_price_change_impact_scd2.sql`.
- Highlight **Kimbo Shortening (PRD-009)**:
  - 180 KES price window (2026-09-01 to 2026-10-03): 158 orders, 466 units, KES 83,700 gross.
  - 215 KES price window (2026-10-03 to 2026-10-04): 6 orders, 20 units, KES 4,290 gross.
  - 255 KES active price window (2026-10-04 onwards): 3 orders, 8 units, KES 2,020 gross.
- Explain how the as-of join preserved historical revenue accuracy without retroactive distortion.

**Spoken Script:**
> *"Finally, querying our product performance mart demonstrates SCD Type 2 correctness, proving that price changes preserve exact historical revenues without retroactive distortion."*

---

## Screenshot Artifact Checklist

Refer to [`docs/screenshots/README.md`](screenshots/README.md) for target filenames, recommended capture resolutions, and framing details.
