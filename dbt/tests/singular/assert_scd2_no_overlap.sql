-- Singular Test: assert_scd2_no_overlap
-- Fails if any customer or product has overlapping validity windows in their SCD2 snapshot tables.

with customer_overlaps as (
    select
        a.customer_id as entity_id,
        'customer' as entity_type,
        a.dbt_scd_id as scd_id_a,
        b.dbt_scd_id as scd_id_b,
        a.dbt_valid_from as a_valid_from,
        a.dbt_valid_to as a_valid_to,
        b.dbt_valid_from as b_valid_from,
        b.dbt_valid_to as b_valid_to
    from {{ ref('snap_customers') }} as a
    inner join {{ ref('snap_customers') }} as b
        on
            a.customer_id = b.customer_id
            and a.dbt_scd_id != b.dbt_scd_id
            and a.dbt_valid_from < b.dbt_valid_from
            and coalesce(a.dbt_valid_to, timestamp '9999-12-31') > b.dbt_valid_from
),

product_overlaps as (
    select
        a.product_id as entity_id,
        'product' as entity_type,
        a.dbt_scd_id as scd_id_a,
        b.dbt_scd_id as scd_id_b,
        a.dbt_valid_from as a_valid_from,
        a.dbt_valid_to as a_valid_to,
        b.dbt_valid_from as b_valid_from,
        b.dbt_valid_to as b_valid_to
    from {{ ref('snap_products') }} as a
    inner join {{ ref('snap_products') }} as b
        on
            a.product_id = b.product_id
            and a.dbt_scd_id != b.dbt_scd_id
            and a.dbt_valid_from < b.dbt_valid_from
            and coalesce(a.dbt_valid_to, timestamp '9999-12-31') > b.dbt_valid_from
)

select * from customer_overlaps
union all
select * from product_overlaps
