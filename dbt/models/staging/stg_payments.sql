with source as (
    select * from {{ source('raw', 'payments') }}
),

renamed as (
    select
        cast(trim(payment_id) as varchar) as payment_id,
        cast(trim(order_id) as varchar) as order_id,
        cast(trim(method) as varchar) as payment_method,
        cast(amount_kes as decimal(10, 2)) as amount_kes,
        cast(paid_at as timestamp) as paid_at,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
