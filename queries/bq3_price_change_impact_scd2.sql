-- Question: BQ-3 - How did price adjustments impact volume and revenue, and how is SCD2 point-in-time history preserved?
-- Grain: One row per product SCD2 price validity window (product_sk).
-- What to look for:
--   1. Products with multiple SCD2 price versions (e.g. Kimbo Shortening PRD-009, Geisha Soap PRD-005) when history advances.
--   2. Orders and units sold correctly partitioned into distinct validity windows (price_valid_from to price_valid_to).
--   3. Historical orders priced at the rate active when placed without retroactive restatement.

WITH multi_version_products AS (
    SELECT product_id
    FROM mrt_product_perf
    GROUP BY product_id
    HAVING COUNT(*) > 1
),
candidate_products AS (
    SELECT product_id FROM multi_version_products
    UNION ALL
    -- Fallback to top catalog products when warehouse is on baseline 30 days
    SELECT product_id FROM mrt_product_perf
    WHERE NOT EXISTS (SELECT 1 FROM multi_version_products)
    LIMIT 5
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.unit_price_kes,
    strftime(p.price_valid_from, '%Y-%m-%d %H:%M') AS valid_from,
    COALESCE(strftime(p.price_valid_to, '%Y-%m-%d %H:%M'), 'ACTIVE (CURRENT)') AS valid_to,
    p.is_current_price,
    p.total_orders,
    p.units_sold,
    ROUND(p.gross_revenue_kes, 2) AS gross_revenue_kes
FROM mrt_product_perf AS p
WHERE p.product_id IN (SELECT product_id FROM candidate_products)
ORDER BY
    p.product_id ASC,
    p.price_valid_from ASC;
