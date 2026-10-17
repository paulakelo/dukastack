with orders as (
    select
        order_id,
        shop_id,
        customer_id,
        order_ts,
        order_status,
        updated_at as order_updated_at
    from {{ ref('stg_orders') }}
),

order_items as (
    select
        order_item_id,
        order_id,
        product_id,
        quantity,
        discount_kes,
        updated_at as item_updated_at
    from {{ ref('stg_order_items') }}
),

orders_and_items as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        oi.quantity,
        oi.discount_kes,
        o.shop_id,
        o.customer_id,
        o.order_ts,
        o.order_status,
        greatest(oi.item_updated_at, o.order_updated_at) as updated_at
    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
),

joined as (
    select
        oai.order_item_id,
        oai.order_id,
        s.shop_sk,
        c.customer_sk,
        p.product_sk,
        oai.order_ts,
        oai.order_status,
        oai.quantity,
        p.unit_price_kes,
        oai.discount_kes,
        oai.updated_at,
        cast(oai.order_ts as date) as order_date,
        cast(
            (oai.quantity * p.unit_price_kes) - oai.discount_kes as decimal(10, 2)
        ) as line_amount_kes
    from orders_and_items as oai
    left join {{ ref('dim_shops') }} as s
        on oai.shop_id = s.shop_id
    {{ as_of_join(ref('dim_customers'), 'oai', 'c', 'customer_id') }}
    {{ as_of_join(ref('dim_products'), 'oai', 'p', 'product_id') }}
)

select
    order_item_id,
    order_id,
    shop_sk,
    customer_sk,
    product_sk,
    order_date,
    order_ts,
    order_status,
    quantity,
    unit_price_kes,
    discount_kes,
    line_amount_kes,
    updated_at
from joined
