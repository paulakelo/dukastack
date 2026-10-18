# DukaStack Sample Warehouse Queries

Automated results executed against `data/dukastack.duckdb`.

To re-render these results, run:

```bash
make queries
```

---

## BQ1: BQ-1 - How do retail shops compare in total sales volume, refund impact, and net revenue?

**Grain:** One row per retail shop (aggregated across the reporting date range).

**What to look for:**
- 1. Total gross revenue vs net revenue per shop across Kenyan counties.
- 2. Refund rates (refund_amount_kes / gross_sales_kes) identifying shops with elevated return rates.
- 3. Average order value (net_sales_kes / total_orders) reflecting basket sizing by location.

```sql
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
```

### Results (Top 10 rows)

| shop_id | shop_name                       | county  | total_orders | total_items_sold | total_items_refunded | gross_sales_kes | refund_amount_kes | net_sales_kes | refund_rate_pct | avg_order_value_kes |
| ------- | ------------------------------- | ------- | ------------ | ---------------- | -------------------- | --------------- | ----------------- | ------------- | --------------- | ------------------- |
| SHP-002 | Mama Oliech Kiosk - Kisumu      | Kisumu  | 146          | 1118             | 117                  | 214820.00       | 20295.00          | 194525.00     | 9.45            | 1332.36             |
| SHP-005 | Thika Road Corner Duka - Kiambu | Kiambu  | 144          | 1157             | 153                  | 222575.00       | 30565.00          | 192010.00     | 13.73           | 1333.4              |
| SHP-003 | Coast Breeze Stores - Mombasa   | Mombasa | 144          | 1127             | 158                  | 216695.00       | 34355.00          | 182340.00     | 15.85           | 1266.25             |
| SHP-004 | Rift Valley Provisions - Nakuru | Nakuru  | 143          | 1018             | 106                  | 188155.00       | 19865.00          | 168290.00     | 10.56           | 1176.85             |
| SHP-001 | Duka Mwangi - Nairobi CBD       | Nairobi | 137          | 1000             | 115                  | 184240.00       | 22975.00          | 161265.00     | 12.47           | 1177.12             |

---

## BQ2: BQ-2 - Which fast-moving products exhibit the highest stockout risk based on daily unit run-rate?

**Grain:** One row per product SKU.

**What to look for:**
- 1. Products with the highest total units sold and daily sales velocity.
- 2. Order penetration (number of distinct customer orders containing the SKU).
- 3. Fast depletion items in high-frequency categories (Food Cupboard, Dairy, Beverages) requiring replenishment.

```sql
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
```

### Results (Top 10 rows)

| product_id | product_name                | category      | current_price_kes | total_orders | total_units_sold | gross_revenue_kes | avg_units_per_day |
| ---------- | --------------------------- | ------------- | ----------------- | ------------ | ---------------- | ----------------- | ----------------- |
| PRD-003    | Brookside Milk 500ml        | Dairy         | 65.00             | 172          | 496              | 32050.00          | 16.5              |
| PRD-007    | Ketepa Tea Leaves 250g      | Beverages     | 140.00            | 161          | 483              | 67460.00          | 16.1              |
| PRD-008    | Kensalt Table Salt 1kg      | Food Cupboard | 45.00             | 154          | 474              | 21180.00          | 15.8              |
| PRD-012    | Sunlight Washing Powder 1kg | Personal Care | 260.00            | 139          | 459              | 119210.00         | 15.3              |
| PRD-010    | Royco Cubes 40s             | Food Cupboard | 120.00            | 154          | 457              | 54670.00          | 15.2              |
| PRD-004    | Tusker Lager 500ml          | Beverages     | 220.00            | 147          | 448              | 98380.00          | 14.9              |
| PRD-005    | Geisha Soap 225g            | Personal Care | 110.00            | 149          | 447              | 48990.00          | 14.9              |
| PRD-009    | Kimbo Shortening 500g       | Food Cupboard | 180.00            | 150          | 441              | 79210.00          | 14.7              |
| PRD-002    | Salit Cooking Oil 1L        | Food Cupboard | 320.00            | 138          | 439              | 140330.00         | 14.6              |
| PRD-001    | Unga Wa Dola 2kg            | Food Cupboard | 210.00            | 133          | 433              | 90780.00          | 14.4              |

---

## BQ3: BQ-3 - How did price adjustments impact volume and revenue, and how is SCD2 point-in-time history preserved?

**Grain:** One row per product SCD2 price validity window (product_sk).

**What to look for:**
- 1. Products with multiple SCD2 price versions (e.g. Kimbo Shortening PRD-009, Geisha Soap PRD-005) when history advances.
- 2. Orders and units sold correctly partitioned into distinct validity windows (price_valid_from to price_valid_to).
- 3. Historical orders priced at the rate active when placed without retroactive restatement.

```sql
WITH multi_version_products AS (
    SELECT product_id
    FROM mrt_product_perf
    GROUP BY product_id
    HAVING COUNT(*) > 1
),
candidate_products AS (
    SELECT product_id FROM multi_version_products
    UNION ALL
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
```

### Results (Top 10 rows)

| product_id | product_name         | category      | unit_price_kes | valid_from       | valid_to         | is_current_price | total_orders | units_sold | gross_revenue_kes |
| ---------- | -------------------- | ------------- | -------------- | ---------------- | ---------------- | ---------------- | ------------ | ---------- | ----------------- |
| PRD-001    | Unga Wa Dola 2kg     | Food Cupboard | 210.00         | 2026-09-01 08:00 | ACTIVE (CURRENT) | True             | 133          | 433        | 90780.00          |
| PRD-002    | Salit Cooking Oil 1L | Food Cupboard | 320.00         | 2026-09-01 08:00 | ACTIVE (CURRENT) | True             | 138          | 439        | 140330.00         |
| PRD-003    | Brookside Milk 500ml | Dairy         | 65.00          | 2026-09-01 08:00 | ACTIVE (CURRENT) | True             | 172          | 496        | 32050.00          |
| PRD-004    | Tusker Lager 500ml   | Beverages     | 220.00         | 2026-09-01 08:00 | ACTIVE (CURRENT) | True             | 147          | 448        | 98380.00          |
| PRD-005    | Geisha Soap 225g     | Personal Care | 110.00         | 2026-09-01 08:00 | ACTIVE (CURRENT) | True             | 149          | 447        | 48990.00          |

---

## BQ4: BQ-4 - Which catalog products are slow movers with the lowest sales volume and order counts?

**Grain:** One row per product SKU.

**What to look for:**
- 1. Products with the lowest cumulative sales volume (units sold) and order frequency.
- 2. Gross revenue contribution relative to overall catalog turnover.
- 3. Candidates for shelf-space rationalization, clearance discounts, or inventory reduction.

```sql
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
```

### Results (Top 10 rows)

| product_id | product_name                | category      | current_price_kes | total_orders | total_units_sold | gross_revenue_kes |
| ---------- | --------------------------- | ------------- | ----------------- | ------------ | ---------------- | ----------------- |
| PRD-006    | Pembe Maize Flour 2kg       | Food Cupboard | 195.00            | 134          | 411              | 80045.00          |
| PRD-011    | Dawaat Basmati Rice 2kg     | Food Cupboard | 450.00            | 141          | 432              | 194180.00         |
| PRD-001    | Unga Wa Dola 2kg            | Food Cupboard | 210.00            | 133          | 433              | 90780.00          |
| PRD-002    | Salit Cooking Oil 1L        | Food Cupboard | 320.00            | 138          | 439              | 140330.00         |
| PRD-009    | Kimbo Shortening 500g       | Food Cupboard | 180.00            | 150          | 441              | 79210.00          |
| PRD-005    | Geisha Soap 225g            | Personal Care | 110.00            | 149          | 447              | 48990.00          |
| PRD-004    | Tusker Lager 500ml          | Beverages     | 220.00            | 147          | 448              | 98380.00          |
| PRD-010    | Royco Cubes 40s             | Food Cupboard | 120.00            | 154          | 457              | 54670.00          |
| PRD-012    | Sunlight Washing Powder 1kg | Personal Care | 260.00            | 139          | 459              | 119210.00         |
| PRD-008    | Kensalt Table Salt 1kg      | Food Cupboard | 45.00             | 154          | 474              | 21180.00          |

---

## BQ5: BQ-5 - What is the data freshness and operational health across retail shops and pipeline layers?

**Grain:** One row per retail shop.

**What to look for:**
- 1. Latest order date processed per shop in the marts, verifying synchronous pipeline ingestion.
- 2. Total active reporting days spanning the warehouse date range.
- 3. Aggregate order volume and sales revenue confirming continuous, uninterrupted POS operations.

```sql
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
```

### Results (Top 10 rows)

| shop_id | shop_name                       | county  | first_order_date | latest_order_date | active_reporting_days | total_orders | total_items_sold | total_net_sales_kes |
| ------- | ------------------------------- | ------- | ---------------- | ----------------- | --------------------- | ------------ | ---------------- | ------------------- |
| SHP-001 | Duka Mwangi - Nairobi CBD       | Nairobi | 2026-09-02       | 2026-10-01        | 30                    | 137          | 1000             | 161265.00           |
| SHP-002 | Mama Oliech Kiosk - Kisumu      | Kisumu  | 2026-09-02       | 2026-10-01        | 30                    | 146          | 1118             | 194525.00           |
| SHP-003 | Coast Breeze Stores - Mombasa   | Mombasa | 2026-09-02       | 2026-10-01        | 30                    | 144          | 1127             | 182340.00           |
| SHP-004 | Rift Valley Provisions - Nakuru | Nakuru  | 2026-09-02       | 2026-10-01        | 29                    | 143          | 1018             | 168290.00           |
| SHP-005 | Thika Road Corner Duka - Kiambu | Kiambu  | 2026-09-02       | 2026-10-01        | 29                    | 144          | 1157             | 192010.00           |

---
