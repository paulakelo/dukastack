with product_snapshots as (
    select
        product_id,
        product_name,
        category,
        unit_price_kes,
        dbt_valid_from as valid_from,
        dbt_valid_to as valid_to,
        dbt_valid_to is null as is_current
    from {{ ref('snap_products') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['product_id', 'valid_from']) }} as product_sk,
    product_id,
    product_name,
    category,
    unit_price_kes,
    valid_from,
    valid_to,
    is_current
from product_snapshots
