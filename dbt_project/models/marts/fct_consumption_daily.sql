-- Daily kWh per meter with completeness and the DQ-4 quality flag (FR-08, FR-22).

select
    meter_id,
    feeder_id,
    zone_id,
    interval_date_ist,
    coalesce(sum(delta_kwh), 0)::decimal(18, 4) as consumption_kwh,
    count(*) as intervals_expected,
    count(reading_ts) as intervals_received,
    count(*) filter (where is_gap) as gap_intervals,
    count(*) filter (where dq_flag = 'register_decrease') as register_decrease_intervals,
    round(100.0 * count(reading_ts) / count(*), 2)::decimal(6, 2) as completeness_pct,
    case
        when count(reading_ts) < count(*) * {{ var('completeness_threshold') }}
            then 'LOW_COMPLETENESS'
        else 'OK'
    end as quality_flag
from {{ ref('int_meter_intervals') }}
group by meter_id, feeder_id, zone_id, interval_date_ist
