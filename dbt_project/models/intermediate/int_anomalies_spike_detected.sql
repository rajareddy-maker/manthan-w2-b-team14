-- SPIKE (FR-11, ADR-006): interval kWh z-score > spike_z_threshold vs the meter's own trailing
-- spike_history_days (>= spike_min_points clean points) AND kWh >= spike_min_multiple x the
-- trailing mean. Only clean intervals (received, no gap spanned, delta known) are used.
-- Consecutive flagged intervals of one meter are merged into one event.

with clean as (
    select
        meter_id,
        feeder_id,
        zone_id,
        interval_start_ts,
        delta_kwh::double as kwh
    from {{ ref('int_meter_intervals') }}
    where delta_kwh is not null and gap_intervals = 0
),

stats as (
    select
        *,
        avg(kwh) over w as mean_kwh,
        stddev_samp(kwh) over w as std_kwh,
        count(*) over w as history_points
    from clean
    window w as (
        partition by meter_id
        order by epoch(interval_start_ts)
        range between {{ var('spike_history_days') * 86400 }} preceding and 1 preceding
    )
),

flagged as (
    select
        *,
        (kwh - mean_kwh) / std_kwh as z_score
    from stats
    where
        history_points >= {{ var('spike_min_points') }}
        and std_kwh > 0
        and (kwh - mean_kwh) / std_kwh > {{ var('spike_z_threshold') }}
        and kwh >= {{ var('spike_min_multiple') }} * mean_kwh
),

islands as (
    select
        *,
        epoch(interval_start_ts) / ({{ var('interval_minutes') }} * 60)
        - row_number() over (partition by meter_id order by interval_start_ts) as island
    from flagged
)

select
    'SPIKE' as anomaly_type,
    meter_id,
    feeder_id,
    zone_id,
    min(interval_start_ts) as start_ts,
    max(interval_start_ts) + interval {{ var('interval_minutes') }} minute as end_ts,
    count(*) as intervals,
    'max_z_score' as metric_name,
    round(max(z_score), 3)::decimal(12, 3) as metric_value,
    {{ var('spike_z_threshold') }}::decimal(12, 3) as threshold,
    1 as affected_meters,
    round(max(kwh), 4)::decimal(18, 4) as peak_kwh
from islands
group by meter_id, feeder_id, zone_id, island
