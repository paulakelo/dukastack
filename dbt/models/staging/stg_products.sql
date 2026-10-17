with source as (
    select * from {{ source('raw', 'products') }}
),

renamed as (
    select
        cast(trim(product_id) as varchar) as product_id,
        cast(trim(product_name) as varchar) as product_name,
        cast(trim(category) as varchar) as category,
        cast(unit_price_kes as decimal(10, 2)) as unit_price_kes,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
