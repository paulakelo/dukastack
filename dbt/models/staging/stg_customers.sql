with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        cast(trim(customer_id) as varchar) as customer_id,
        cast(trim(customer_name) as varchar) as customer_name,
        cast(trim(county) as varchar) as county,
        cast(trim(loyalty_tier) as varchar) as loyalty_tier,
        cast(updated_at as timestamp) as updated_at,
        cast(_loaded_at as timestamp) as _loaded_at
    from source
)

select * from renamed
