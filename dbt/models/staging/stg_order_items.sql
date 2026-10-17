with source as (
    select * from {{ source('raw', 'order_items') }}
),

renamed as (
    select
        cast(trim(order_item_id) as varchar) as order_item_id,
        cast(trim(order_id) as varchar) as order_id,
        cast(trim(product_id) as varchar) as product_id,
        cast(quantity as integer) as quantity,
        cast(discount_kes as decimal(10, 2)) as discount_kes,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
