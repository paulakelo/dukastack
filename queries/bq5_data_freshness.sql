-- Question: BQ-5 - What is the data freshness and operational health across retail shops and pipeline layers?
-- Grain: One row per retail shop.
-- What to look for:
--   1. Latest order date processed per shop in the marts, verifying synchronous pipeline ingestion.
--   2. Total active reporting days spanning the warehouse date range.
--   3. Aggregate order volume and sales revenue confirming continuous, uninterrupted POS operations.

SELECT
    shop_id,
    shop_name,
    county,
    MIN(order_date) AS first_order_date,
    MAX(order_date) AS latest_order_date,
    COUNT(DISTINCT order_date) AS active_reporting_days,
    SUM(total_orders) AS total_orders,
    SUM(items_sold) AS total_items_sold,
    ROUND(SUM(net_sales_kes), 2) AS total_net_sales_kes
FROM mrt_daily_sales
GROUP BY
    shop_id,
    shop_name,
    county
ORDER BY
    latest_order_date DESC,
    shop_id ASC;
