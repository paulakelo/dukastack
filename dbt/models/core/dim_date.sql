with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2026-01-01' as date)",
        end_date="cast('2027-12-31' as date)"
    ) }}
),

casted as (
    select cast(date_day as date) as date_day
    from date_spine
),

calculated as (
    select
        date_day,
        date_day as date_key,
        cast(extract(year from date_day) as integer) as date_year,
        cast(extract(quarter from date_day) as integer) as date_quarter,
        cast(extract(month from date_day) as integer) as date_month,
        cast(extract(day from date_day) as integer) as day_of_month,
        cast(dayofweek(date_day) as integer) as day_of_week,
        strftime(date_day, '%B') as month_name,
        strftime(date_day, '%A') as day_name,
        dayofweek(date_day) in (0, 6) as is_weekend
    from casted
)

select
    date_key,
    date_day,
    date_year,
    date_quarter,
    date_month,
    month_name,
    day_of_month,
    day_of_week,
    day_name,
    is_weekend
from calculated
