-- Saved Query: Price and Loyalty Tier in Force at Sale (FR-10)
-- Demonstrates the reconstruction of SCD Type 2 point-in-time dimensions.
-- Usage: Replace 'ORD-SAMPLE-001' with any order_id.

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
from {{ ref('fct_order_items') }} f
join {{ ref('stg_orders') }} o
    on f.order_id = o.order_id
join {{ ref('dim_customers') }} c
    on f.customer_sk = c.customer_sk
join {{ ref('dim_products') }} p
    on f.product_sk = p.product_sk
where f.order_id = 'ORD-SAMPLE-001'
order by f.order_item_id;
