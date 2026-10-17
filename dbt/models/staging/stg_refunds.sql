with source as (
    select * from {{ source('raw', 'refunds') }}
),

renamed as (
    select
        cast(trim(refund_id) as varchar) as refund_id,
        cast(trim(order_item_id) as varchar) as order_item_id,
        cast(quantity as integer) as quantity,
        cast(refund_kes as decimal(10, 2)) as refund_kes,
        cast(refunded_at as timestamp) as refunded_at,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
