-- Saved Query: Customer Loyalty Tier History (M3 Proof)
-- Demonstrates SCD Type 2 tracking with contiguous dbt_valid_from and dbt_valid_to ranges.

select
    customer_id,
    customer_name,
    county,
    loyalty_tier,
    dbt_valid_from,
    dbt_valid_to,
    case
        when dbt_valid_to is null then true
        else false
    end as is_current
from {{ ref('snap_customers') }}
where customer_id = 'CUST-0039'
order by dbt_valid_from asc;
