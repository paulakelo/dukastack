with item_refunds as (
    select
        order_item_id,
        sum(quantity) as items_refunded,
        sum(refund_kes) as refund_amount_kes
    from {{ ref('fct_refunds') }}
    group by order_item_id
),

order_items_with_refunds as (
    select
        oi.order_item_id,
        oi.order_id,
        oi.shop_sk,
        oi.order_date,
        oi.quantity as items_sold,
        oi.line_amount_kes as gross_sales_kes,
        coalesce(r.items_refunded, 0) as items_refunded,
        coalesce(r.refund_amount_kes, 0.00) as refund_amount_kes
    from {{ ref('fct_order_items') }} as oi
    left join item_refunds as r
        on oi.order_item_id = r.order_item_id
),

daily_agg as (
    select
        shop_sk,
        order_date,
        count(distinct order_id) as total_orders,
        sum(items_sold) as items_sold,
        sum(items_refunded) as items_refunded,
        sum(gross_sales_kes) as gross_sales_kes,
        sum(refund_amount_kes) as refund_amount_kes,
        sum(gross_sales_kes) - sum(refund_amount_kes) as net_sales_kes
    from order_items_with_refunds
    group by shop_sk, order_date
),

joined as (
    select
        s.shop_sk,
        s.shop_id,
        s.shop_name,
        s.county,
        da.order_date,
        da.total_orders,
        da.items_sold,
        da.items_refunded,
        da.gross_sales_kes,
        da.refund_amount_kes,
        da.net_sales_kes,
        {{ dbt_utils.generate_surrogate_key(['s.shop_id', 'da.order_date']) }} as daily_sales_sk
    from daily_agg as da
    inner join {{ ref('dim_shops') }} as s
        on da.shop_sk = s.shop_sk
)

select
    daily_sales_sk,
    shop_sk,
    shop_id,
    shop_name,
    county,
    order_date,
    total_orders,
    items_sold,
    items_refunded,
    gross_sales_kes,
    refund_amount_kes,
    net_sales_kes
from joined
