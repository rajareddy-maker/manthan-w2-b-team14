{{ config(materialized='table') }}

-- Every bronze row mapped to the canonical contract (ADR-005), with a reject reason (NULL = valid)
-- and a duplicate rank among valid rows. Downstream reads stg_meter__readings / _quarantine.

with bronze as (
    select
        raw_payload,
        is_valid_json,
        schema_version,
        meter_id,
        source_file,
        line_no,
        file_arrival_ts,
        ingested_at,
        dt as landing_date_ist,
        zone as gateway_zone
    from {{ bronze_meter_readings() }}
),

v1 as (
    select
        *,
        json_extract_string(raw_payload, '$.ts') as source_ts_text,
        try_cast(json_extract_string(raw_payload, '$.energy_wh') as decimal(18, 4)) as source_energy,
        'Wh' as source_unit,
        json_extract_string(raw_payload, '$.status') as status,
        null::decimal(6, 1) as voltage_v,
        null::varchar as firmware_version
    from bronze
    where schema_version = 1
),

v2 as (
    select
        *,
        json_extract_string(raw_payload, '$.ts') as source_ts_text,
        try_cast(json_extract_string(raw_payload, '$.energy') as decimal(18, 4)) as source_energy,
        json_extract_string(raw_payload, '$.unit') as source_unit,
        json_extract_string(raw_payload, '$.status') as status,
        try_cast(json_extract_string(raw_payload, '$.voltage') as decimal(6, 1)) as voltage_v,
        json_extract_string(raw_payload, '$.firmware_version') as firmware_version
    from bronze
    where schema_version = 2
),

unhandled as (
    select *
    from bronze
    where schema_version is null or schema_version not in (1, 2)
),

unioned as (
    select * from v1
    union all by name
    select * from v2
    union all by name
    select * from unhandled
),

parsed as (
    select
        *,
        case
            when regexp_matches(source_ts_text, '([+-]\d{2}:\d{2}|Z)$')
                then try_cast(source_ts_text as timestamptz)
            -- naive timestamps are IST (CLAUDE.md time-zone rule)
            else timezone('{{ var("tz") }}', try_cast(source_ts_text as timestamp))
        end as source_reading_ts,
        case source_unit
            when 'Wh' then source_energy * 0.001
            when 'kWh' then source_energy
        end::decimal(18, 4) as register_kwh
    from unioned
),

snapped as (
    select
        *,
        -- signed distance (s) to the nearest 15-min grid point; IST offset is a multiple of 15 min
        case
            when epoch(source_reading_ts)::bigint % 900 <= 450
                then epoch(source_reading_ts)::bigint % 900
            else epoch(source_reading_ts)::bigint % 900 - 900
        end as snap_seconds
    from parsed
),

checked as (
    select
        s.*,
        s.source_reading_ts - to_seconds(s.snap_seconds) as reading_ts,
        m.feeder_id,
        m.zone_id,
        case
            when not s.is_valid_json then 'invalid_json'
            when s.schema_version is null or s.schema_version not in (1, 2) then 'unknown_schema'
            when s.meter_id is null or s.source_reading_ts is null or s.source_energy is null
                then 'missing_or_unparseable_field'
            when s.source_unit is null or s.source_unit not in ('Wh', 'kWh') then 'unknown_unit'
            when s.source_energy < 0 then 'negative_energy'
            when abs(s.snap_seconds) > {{ var('grid_snap_tolerance_s') }} then 'off_grid'
            when m.meter_id is null then 'unknown_meter'
        end as reject_reason
    from snapped as s
    left join {{ ref('meter_master') }} as m on s.meter_id = m.meter_id
)

select
    meter_id,
    feeder_id,
    zone_id,
    reading_ts,
    reading_ts - interval '{{ var("interval_minutes") }} minutes' as interval_start_ts,
    cast(
        timezone('{{ var("tz") }}', reading_ts - interval '{{ var("interval_minutes") }} minutes')
        as date
    ) as interval_date_ist,
    register_kwh,
    status,
    voltage_v,
    firmware_version,
    schema_version,
    source_reading_ts,
    source_energy,
    source_unit,
    snap_seconds,
    reject_reason,
    case
        when reject_reason is null
            then row_number() over (
                partition by reject_reason is null, meter_id, reading_ts
                order by ingested_at, file_arrival_ts, source_file, line_no
            )
    end as dup_rank,
    raw_payload,
    source_file,
    line_no,
    file_arrival_ts,
    ingested_at,
    landing_date_ist,
    gateway_zone
from checked
