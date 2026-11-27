{% macro bronze_meter_readings() -%}
    {#- Bronze Parquet lake (ADR-003). Path is relative to the repo root (dbt is run from there). -#}
    read_parquet(
        '{{ env_var("BRONZE_ROOT", "data/lake/bronze") }}/*/*/*.parquet',
        hive_partitioning = true,
        hive_types = {'dt': date, 'zone': varchar}
    )
{%- endmacro %}
