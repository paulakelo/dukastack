with shops as (
    select
        shop_id,
        shop_name,
        county,
        updated_at
    from {{ ref('stg_shops') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['shop_id']) }} as shop_sk,
    shop_id,
    shop_name,
    county,
    updated_at
from shops
