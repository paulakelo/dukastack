with source as (
    select * from {{ source('raw', 'shops') }}
),

renamed as (
    select
        cast(trim(shop_id) as varchar) as shop_id,
        cast(trim(shop_name) as varchar) as shop_name,
        cast(trim(county) as varchar) as county,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
