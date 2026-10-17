with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        cast(trim(order_id) as varchar) as order_id,
        cast(trim(shop_id) as varchar) as shop_id,
        cast(trim(customer_id) as varchar) as customer_id,
        cast(order_ts as timestamp) as order_ts,
        cast(trim(order_status) as varchar) as order_status,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
