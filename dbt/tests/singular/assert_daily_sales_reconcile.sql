-- Singular Test: assert_daily_sales_reconcile
-- Verifies that mart aggregates reconcile against underlying fact tables.
-- Net sales in mrt_daily_sales must match gross line sales in fct_order_items
-- minus refunds in fct_refunds.

with mart_totals as (
    select
        coalesce(sum(gross_sales_kes), 0.00) as mart_gross_sales,
        coalesce(sum(refund_amount_kes), 0.00) as mart_refund_amount,
        coalesce(sum(net_sales_kes), 0.00) as mart_net_sales
    from {{ ref('mrt_daily_sales') }}
),

fact_totals as (
    select coalesce(sum(line_amount_kes), 0.00) as fact_gross_sales
    from {{ ref('fct_order_items') }}
),

refund_totals as (
    select coalesce(sum(refund_kes), 0.00) as fact_refunds
    from {{ ref('fct_refunds') }}
),

reconciliation as (
    select
        m.mart_gross_sales,
        f.fact_gross_sales,
        m.mart_refund_amount,
        r.fact_refunds,
        m.mart_net_sales,
        (f.fact_gross_sales - r.fact_refunds) as expected_net_sales,
        abs(m.mart_net_sales - (f.fact_gross_sales - r.fact_refunds)) as net_diff,
        abs(m.mart_gross_sales - f.fact_gross_sales) as gross_diff,
        abs(m.mart_refund_amount - r.fact_refunds) as refund_diff
    from mart_totals as m
    cross join fact_totals as f
    cross join refund_totals as r
)

select
    mart_gross_sales,
    fact_gross_sales,
    mart_refund_amount,
    fact_refunds,
    mart_net_sales,
    expected_net_sales,
    net_diff,
    gross_diff,
    refund_diff
from reconciliation
where
    net_diff > 0.01
    or gross_diff > 0.01
    or refund_diff > 0.01
