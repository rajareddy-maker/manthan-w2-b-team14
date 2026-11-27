{%- set tz = var('tz') -%}
{%- set step = var('interval_minutes') -%}

-- One row per meter (from the master) per 15-min grid slot in the window (FR-07, FR-21).
-- Gaps are marked, never filled. A reading after a gap carries the whole register delta once,
-- with gap_intervals = number of missing slots it spans. Window defaults: first reading's IST date
-- .. last interval date; override with --vars '{window_start: ..., window_end: ...}'.

with readings as (
    select
        r.meter_id,
        r.reading_ts,
        r.interval_start_ts,
        r.register_kwh,
        r.status,
        m.register_max_kwh
    from {{ ref('stg_meter__readings') }} as r
    inner join {{ ref('meter_master') }} as m on r.meter_id = m.meter_id
),

bounds as (
    select
        {% if var('window_start', none) -%}
            date '{{ var("window_start") }}'
        {%- else -%}
            cast(timezone('{{ tz }}', min(reading_ts)) as date)
        {%- endif %} as start_date_ist,
        {% if var('window_end', none) -%}
            date '{{ var("window_end") }}'
        {%- else -%}
            cast(timezone('{{ tz }}', max(interval_start_ts)) as date)
        {%- endif %} as end_date_ist
    from readings
),

ordered as (
    select
        *,
        lag(register_kwh) over w as prev_register_kwh,
        lag(reading_ts) over w as prev_reading_ts
    from readings
    window w as (partition by meter_id order by reading_ts)
),

classified as (
    select
        meter_id,
        reading_ts,
        interval_start_ts,
        register_kwh,
        prev_register_kwh,
        status,
        cast((epoch(reading_ts) - epoch(prev_reading_ts)) / ({{ step }} * 60) as integer) - 1
            as gap_intervals,
        case
            when prev_register_kwh is null then null
            when register_kwh >= prev_register_kwh then register_kwh - prev_register_kwh
            -- legitimate wrap of the cumulative register
            when status = 'ROLLOVER' then (register_max_kwh - prev_register_kwh) + register_kwh
        end::decimal(18, 4) as delta_kwh,
        case
            when prev_register_kwh is null then 'no_previous_reading'
            when register_kwh < prev_register_kwh and status <> 'ROLLOVER' then 'register_decrease'
        end as dq_flag
    from ordered
),

slot_series as (
    select
        unnest(
            generate_series(
                start_date_ist::timestamp,
                end_date_ist::timestamp + interval 1 day - interval {{ step }} minute,
                interval {{ step }} minute
            )
        ) as slot_local
    from bounds
),

grid as (
    select
        m.meter_id,
        m.feeder_id,
        m.zone_id,
        timezone('{{ tz }}', s.slot_local) as interval_start_ts
    from {{ ref('meter_master') }} as m
    cross join slot_series as s
)

select
    g.meter_id,
    g.feeder_id,
    g.zone_id,
    g.interval_start_ts,
    g.interval_start_ts + interval {{ step }} minute as interval_end_ts,
    cast(timezone('{{ tz }}', g.interval_start_ts) as date) as interval_date_ist,
    timezone('{{ tz }}', date_trunc('hour', timezone('{{ tz }}', g.interval_start_ts)))
        as hour_start_ts,
    c.reading_ts,
    c.register_kwh,
    c.prev_register_kwh,
    c.status,
    c.reading_ts is null as is_gap,
    c.gap_intervals,
    c.delta_kwh,
    c.dq_flag
from grid as g
left join classified as c
    on g.meter_id = c.meter_id and g.interval_start_ts = c.interval_start_ts
