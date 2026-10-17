# dukastack: Core Star Schema & As-Of Join Proof (Milestone 4)

This document verifies the SCD Type 2 point-in-time dimension enrichment and as-of join reconstruction in `fct_order_items`.

---

## 1. As-Of Join Boundary Unit Tests

Four boundary conditions were tested in `dbt/models/core/_core__unit_tests.yml`:
1. **Order exactly at `valid_from`**: Joins the newly active version.
2. **Order one second before `valid_to`**: Joins the previous version.
3. **Order after last version (`valid_to IS NULL`)**: Joins the current active version.
4. **Order before first version**: Produces NULL surrogate key (caught by `not_null` schema test).

**Result**:
```text
1 of 1 START unit_test fct_order_items::test_fct_order_items_as_of_join_boundaries
1 of 1 PASS fct_order_items::test_fct_order_items_as_of_join_boundaries [PASS in 0.31s]
```

---

## 2. Point-in-Time Query Verification (`docs/queries/price_and_tier_at_sale.sql`)

### Single Order Detail: `ORD-0000006`

```sql
select
    f.order_id,
    f.order_item_id,
    o.order_ts,
    c.customer_id,
    c.customer_name,
    c.loyalty_tier as tier_at_sale,
    p.product_id,
    p.product_name,
    p.category,
    p.unit_price_kes as price_at_sale,
    f.quantity,
    f.line_amount_kes
from fct_order_items f
join stg_orders o on f.order_id = o.order_id
join dim_customers c on f.customer_sk = c.customer_sk
join dim_products p on f.product_sk = p.product_sk
where f.order_id = 'ORD-0000006'
order by f.order_item_id;
```

**Output**:

| order_id | order_item_id | order_ts | customer_id | customer_name | tier_at_sale | product_id | product_name | category | price_at_sale | quantity | line_amount_kes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORD-0000006 | ITM-00000011 | 2026-09-02 08:06:40 | CUST-0016 | Otieno Musyoka | basic | PRD-012 | Sunlight Washing Powder 1kg | Personal Care | 260.00 | 2 | 520.00 |

---

## 3. Longitudinal Tier & Price Mutation Replay: Customer `CUST-0020`

Customer `CUST-0020` placed orders before and after a loyalty tier promotion from `basic` to `silver`. Notice how the as-of join dynamically reconstructed the accurate tier and prevailing product prices at each transaction timestamp without altering historical records:

| Order ID | Order Timestamp | Prevailing Tier (`tier_at_sale`) | Product Description | Point-in-Time Unit Price (KES) | Quantity | Line Amount (KES) |
| --- | --- | --- | --- | --- | --- | --- |
| `ORD-0000010` | 2026-09-02 16:45:18 | **basic** | Dawaat Basmati Rice 2kg | 450.00 | 5 | 2250.00 |
| `ORD-0000022` | 2026-09-03 17:57:35 | **basic** | Salit Cooking Oil 1L | **320.00** | 2 | 640.00 |
| `ORD-0000065` | 2026-09-05 13:30:16 | **basic** | Royco Cubes 40s | 120.00 | 1 | 120.00 |
| `ORD-0000213` | 2026-09-10 19:08:27 | **silver** | Unga Wa Dola 2kg | 200.00 | 2 | 400.00 |
| `ORD-0000241` | 2026-09-11 10:19:13 | **silver** | Salit Cooking Oil 1L | **325.00** | 3 | 975.00 |
| `ORD-0000251` | 2026-09-12 11:47:52 | **silver** | Tusker Lager 500ml | 290.00 | 2 | 580.00 |
| `ORD-0000281` | 2026-09-13 16:24:18 | **silver** | Sunlight Washing Powder 1kg | 235.00 | 2 | 470.00 |
| `ORD-0000317` | 2026-09-14 14:14:28 | **silver** | Geisha Soap 225g | 100.00 | 1 | 100.00 |
