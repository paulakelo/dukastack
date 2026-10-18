-- Question: BQ-1 - How do retail shops compare in total sales volume, refund impact, and net revenue?
-- Grain: One row per retail shop (aggregated across the reporting date range).
-- What to look for:
--   1. Total gross revenue vs net revenue per shop across Kenyan counties.
--   2. Refund rates (refund_amount_kes / gross_sales_kes) identifying shops with elevated return rates.
--   3. Average order value (net_sales_kes / total_orders) reflecting basket sizing by location.

SELECT
    shop_id,
    shop_name,
    county,
    SUM(total_orders) AS total_orders,
    SUM(items_sold) AS total_items_sold,
    SUM(items_refunded) AS total_items_refunded,
    ROUND(SUM(gross_sales_kes), 2) AS gross_sales_kes,
    ROUND(SUM(refund_amount_kes), 2) AS refund_amount_kes,
    ROUND(SUM(net_sales_kes), 2) AS net_sales_kes,
    ROUND(SUM(refund_amount_kes) * 100.0 / NULLIF(SUM(gross_sales_kes), 0), 2) AS refund_rate_pct,
    ROUND(SUM(net_sales_kes) / NULLIF(SUM(total_orders), 0), 2) AS avg_order_value_kes
FROM mrt_daily_sales
GROUP BY
    shop_id,
    shop_name,
    county
ORDER BY
    net_sales_kes DESC;
