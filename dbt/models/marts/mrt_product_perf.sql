with product_sales as (
    select
        product_sk,
        count(distinct order_id) as total_orders,
        sum(quantity) as units_sold,
        sum(line_amount_kes) as gross_revenue_kes
    from {{ ref('fct_order_items') }}
    group by product_sk
),

joined as (
    select
        p.product_sk,
        p.product_id,
        p.product_name,
        p.category,
        p.unit_price_kes,
        p.valid_from as price_valid_from,
        p.valid_to as price_valid_to,
        p.is_current as is_current_price,
        coalesce(ps.total_orders, 0) as total_orders,
        coalesce(ps.units_sold, 0) as units_sold,
        coalesce(ps.gross_revenue_kes, 0.00) as gross_revenue_kes
    from {{ ref('dim_products') }} as p
    left join product_sales as ps
        on p.product_sk = ps.product_sk
)

select
    product_sk,
    product_id,
    product_name,
    category,
    unit_price_kes,
    price_valid_from,
    price_valid_to,
    is_current_price,
    total_orders,
    units_sold,
    gross_revenue_kes
from joined
