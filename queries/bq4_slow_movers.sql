-- Question: BQ-4 - Which catalog products are slow movers with the lowest sales volume and order counts?
-- Grain: One row per product SKU.
-- What to look for:
--   1. Products with the lowest cumulative sales volume (units sold) and order frequency.
--   2. Gross revenue contribution relative to overall catalog turnover.
--   3. Candidates for shelf-space rationalization, clearance discounts, or inventory reduction.

SELECT
    product_id,
    product_name,
    category,
    MAX(CASE WHEN is_current_price THEN unit_price_kes END) AS current_price_kes,
    SUM(total_orders) AS total_orders,
    SUM(units_sold) AS total_units_sold,
    ROUND(SUM(gross_revenue_kes), 2) AS gross_revenue_kes
FROM mrt_product_perf
GROUP BY
    product_id,
    product_name,
    category
ORDER BY
    total_units_sold ASC,
    total_orders ASC;
