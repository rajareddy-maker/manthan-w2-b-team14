-- US-12 AC1 / NFR-11: per meter-day, Σ hourly kWh = Σ register deltas recomputed directly from
-- staging (independent of int_meter_intervals). Difference must be exactly 0.
with staged as (
    select
        r.meter_id,
        r.interval_date_ist,
        r.register_kwh,
        r.status,
        m.register_max_kwh,
        lag(r.register_kwh) over (partition by r.meter_id order by r.reading_ts) as prev_kwh
    from {{ ref('stg_meter__readings') }} as r
    inner join {{ ref('meter_master') }} as m on r.meter_id = m.meter_id
),

staged_daily as (
    select
        meter_id,
        interval_date_ist,
        coalesce(sum(
            case
                when register_kwh >= prev_kwh then register_kwh - prev_kwh
                when status = 'ROLLOVER' then register_max_kwh - prev_kwh + register_kwh
            end
        ), 0) as staged_kwh
    from staged
    group by meter_id, interval_date_ist
),

hourly_daily as (
    select
        meter_id,
        interval_date_ist,
        sum(consumption_kwh) as hourly_kwh
    from {{ ref('fct_consumption_hourly') }}
    group by meter_id, interval_date_ist
)

select
    h.meter_id,
    h.interval_date_ist,
    h.hourly_kwh,
    s.staged_kwh
from hourly_daily as h
left join staged_daily as s
    on h.meter_id = s.meter_id and h.interval_date_ist = s.interval_date_ist
where h.hourly_kwh <> coalesce(s.staged_kwh, 0)
