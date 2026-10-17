-- Singular Test: assert_snapshot_matches_source
-- Catches Chaos Scenario C1: Retroactive price changes where updated_at was back-dated
-- and bypassed timestamp snapshot tracking. Fails if active snapshot record diverges from source.

with product_mismatches as (
    select
        p.product_id as entity_id,
        'product' as entity_type,
        cast(p.unit_price_kes as varchar) as source_value,
        cast(s.unit_price_kes as varchar) as snapshot_value
    from {{ ref('stg_products') }} as p
    inner join {{ ref('snap_products') }} as s
        on
            p.product_id = s.product_id
            and s.dbt_valid_to is null
    where p.unit_price_kes != s.unit_price_kes
),

customer_mismatches as (
    select
        c.customer_id as entity_id,
        'customer' as entity_type,
        c.loyalty_tier as source_value,
        s.loyalty_tier as snapshot_value
    from {{ ref('stg_customers') }} as c
    inner join {{ ref('snap_customers') }} as s
        on
            c.customer_id = s.customer_id
            and s.dbt_valid_to is null
    where c.loyalty_tier != s.loyalty_tier
)

select * from product_mismatches
union all
select * from customer_mismatches
