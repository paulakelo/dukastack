-- Singular Test: assert_payments_within_order_total
-- Catches Chaos Scenario C5: Overpaid orders where total payments
-- exceed the computed order item amount.

with payments_by_order as (
    select
        order_id,
        sum(amount_kes) as total_paid_kes
    from {{ ref('stg_payments') }}
    group by order_id
),

order_totals as (
    select
        order_id,
        sum(line_amount_kes) as total_order_kes
    from {{ ref('fct_order_items') }}
    group by order_id
),

overpaid_orders as (
    select
        p.order_id,
        p.total_paid_kes,
        coalesce(o.total_order_kes, 0.00) as total_order_kes,
        (p.total_paid_kes - coalesce(o.total_order_kes, 0.00)) as overpaid_kes
    from payments_by_order as p
    inner join order_totals as o
        on p.order_id = o.order_id
    where (p.total_paid_kes - coalesce(o.total_order_kes, 0.00)) > 0.01
)

select
    order_id,
    total_paid_kes,
    total_order_kes,
    overpaid_kes
from overpaid_orders
