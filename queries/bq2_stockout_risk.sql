-- Question: BQ-2 - Which fast-moving products exhibit the highest stockout risk based on daily unit run-rate?
-- Grain: One row per product SKU.
-- What to look for:
--   1. Products with the highest total units sold and daily sales velocity.
--   2. Order penetration (number of distinct customer orders containing the SKU).
--   3. Fast depletion items in high-frequency categories (Food Cupboard, Dairy, Beverages) requiring replenishment.

WITH days AS (
    SELECT COUNT(DISTINCT order_date) AS active_days FROM mrt_daily_sales
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    MAX(CASE WHEN p.is_current_price THEN p.unit_price_kes END) AS current_price_kes,
    SUM(p.total_orders) AS total_orders,
    SUM(p.units_sold) AS total_units_sold,
    ROUND(SUM(p.gross_revenue_kes), 2) AS gross_revenue_kes,
    ROUND(SUM(p.units_sold)::DOUBLE / MAX(d.active_days), 1) AS avg_units_per_day
FROM mrt_product_perf AS p
CROSS JOIN days AS d
GROUP BY
    p.product_id,
    p.product_name,
    p.category
ORDER BY
    total_units_sold DESC;
