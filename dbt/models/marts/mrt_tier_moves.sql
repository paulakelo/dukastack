with customer_versions as (
    select
        customer_sk,
        customer_id,
        customer_name,
        county,
        loyalty_tier as current_tier,
        valid_from as valid_from_ts,
        valid_to as valid_to_ts,
        is_current,
        lag(loyalty_tier) over (
            partition by customer_id
            order by valid_from
        ) as previous_tier
    from {{ ref('dim_customers') }}
),

tier_spend as (
    select
        customer_sk,
        count(distinct order_id) as total_orders,
        sum(quantity) as items_purchased,
        sum(line_amount_kes) as total_spend_kes
    from {{ ref('fct_order_items') }}
    group by customer_sk
),

joined as (
    select
        cv.customer_sk,
        cv.customer_id,
        cv.customer_name,
        cv.county,
        cv.previous_tier,
        cv.current_tier,
        cv.valid_from_ts,
        cv.valid_to_ts,
        cv.is_current,
        coalesce(ts.total_orders, 0) as total_orders,
        coalesce(ts.items_purchased, 0) as items_purchased,
        coalesce(ts.total_spend_kes, 0.00) as total_spend_kes
    from customer_versions as cv
    left join tier_spend as ts
        on cv.customer_sk = ts.customer_sk
)

select
    customer_sk,
    customer_id,
    customer_name,
    county,
    previous_tier,
    current_tier,
    valid_from_ts,
    valid_to_ts,
    is_current,
    total_orders,
    items_purchased,
    total_spend_kes
from joined
