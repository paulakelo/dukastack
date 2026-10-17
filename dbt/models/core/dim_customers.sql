with customer_snapshots as (
    select
        customer_id,
        customer_name,
        county,
        loyalty_tier,
        dbt_valid_from as valid_from,
        dbt_valid_to as valid_to,
        dbt_valid_to is null as is_current
    from {{ ref('snap_customers') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['customer_id', 'valid_from']) }} as customer_sk,
    customer_id,
    customer_name,
    county,
    loyalty_tier,
    valid_from,
    valid_to,
    is_current
from customer_snapshots
