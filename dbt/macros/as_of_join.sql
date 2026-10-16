{#
    as_of_join Macro:
    Performs point-in-time lookup against SCD Type 2 dimension tables.
    Boundary conditions:
      1. order_ts == valid_from -> matches current version
      2. order_ts == valid_to - 1 sec -> matches previous version
      3. order_ts >= last version valid_from -> matches active version (valid_to is null)
      4. order_ts < first version valid_from -> no match (returns NULL key for loud test failure)
#}

{% macro as_of_join(dim_ref, fact_alias, dim_alias, join_key, ts_col='order_ts', valid_from_col='valid_from', valid_to_col='valid_to') %}
left join {{ dim_ref }} {{ dim_alias }}
    on {{ dim_alias }}.{{ join_key }} = {{ fact_alias }}.{{ join_key }}
   and {{ fact_alias }}.{{ ts_col }} >= {{ dim_alias }}.{{ valid_from_col }}
   and {{ fact_alias }}.{{ ts_col }} < coalesce({{ dim_alias }}.{{ valid_to_col }}, timestamp '9999-12-31')
{% endmacro %}
