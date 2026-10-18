# DukaStack Demo Screenshot Checklist

This directory contains visual captures of the key demo surfaces in **dukastack**.
Follow the checklist below to capture each view during or after running the demo workflow.

> [!NOTE]
> Never fabricate screenshots. Real UI captures ensure full authenticity for presentations, portfolios, and documentation.

---

## Target Screenshot Checklist

| Filename | Surface | Description & Framing | How to Capture |
| :--- | :--- | :--- | :--- |
| `01_dbt_lineage_mart.png` | **dbt Docs** | Lineage graph focused on `mrt_daily_sales` or `mrt_product_perf`. Frame the graph showing upstream staging views, core dimensions/facts, and downstream business exposures (`BQ-1` through `BQ-5`). | 1. Run `make docs-serve`<br>2. Open `http://localhost:8080/#!/overview`<br>3. Click the Lineage Graph icon in bottom right<br>4. Select `mrt_daily_sales` or `mrt_product_perf` |
| `02_dagster_asset_graph.png` | **Dagster UI** | Global software-defined asset graph showing all pipeline asset groups: `raw_pos_data`, `staging`, `snapshots`, `core`, and `marts`. | 1. Run `make dagster`<br>2. Open `http://localhost:3000`<br>3. Navigate to **Deployment** -> **Assets**<br>4. Zoom to fit the complete graph |
| `03_failed_asset_check.png` | **Dagster / dbt** | Visual failure of `unique_stg_order_items_order_item_id` asset check/test after running `make demo-fail`, showing downstream marts blocked (skipped). | 1. Run `make demo-fail`<br>2. In Dagster UI, open the run details or asset check page for `stg_order_items`<br>3. Highlight red failed check and skipped downstream assets |
| `04_passing_run.png` | **Dagster / dbt** | 100% green passing run after executing `make demo-recover`, showing all models, snapshots, and asset checks passing. | 1. Run `make demo-recover`<br>2. In Dagster UI, open **Runs** and select the completed recovery run<br>3. Verify all steps display green checkmarks |
| `05_sample_query_scd2.png` | **Query Results** | Output of BQ-3 demonstrating SCD Type 2 point-in-time correctness for products with price transitions (e.g. Kimbo Shortening PRD-009). | 1. Run `make queries`<br>2. Display `docs/sample_queries.md` rendered in browser or terminal output of `queries/bq3_price_change_impact_scd2.sql` |

---

## Recommended Capture Guidelines

- **Resolution:** 1920x1080 (16:9) or higher.
- **Theme:** Dark mode preferred where available for crisp contrast.
- **Format:** PNG with clean cropping (avoid browser bookmarks bar or OS taskbars).
