{{
    config(
        materialized='incremental',
        unique_key='refund_id',
        incremental_strategy='delete+insert'
    )
}}

with refunds as (
    select
        refund_id,
        order_item_id,
        refunded_at,
        quantity,
        refund_kes,
        updated_at
    from {{ ref('stg_refunds') }}
    {% if is_incremental() %}
        where updated_at >= (
            select date_add(max(this.updated_at), interval '-7 day') from {{ this }} as this
        )
    {% endif %}
),

calculated as (
    select
        refund_id,
        order_item_id,
        refunded_at,
        quantity,
        refund_kes,
        updated_at,
        cast(refunded_at as date) as refund_date
    from refunds
)

select
    refund_id,
    order_item_id,
    refund_date,
    refunded_at,
    quantity,
    refund_kes,
    updated_at
from calculated
