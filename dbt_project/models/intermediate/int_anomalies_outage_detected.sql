-- OUTAGE (FR-13): >= outage_missing_share of a feeder's master meters miss the same interval,
-- for >= outage_min_intervals consecutive intervals. One event per feeder per contiguous run.

with feeder_size as (
    select
        feeder_id,
        count(*) as meters
    from {{ ref('meter_master') }}
    group by feeder_id
),

slot_missing as (
    select
        feeder_id,
        zone_id,
        interval_start_ts,
        count(*) filter (where is_gap) as missing_meters
    from {{ ref('int_meter_intervals') }}
    group by feeder_id, zone_id, interval_start_ts
),

flagged as (
    select
        s.*,
        f.meters,
        s.missing_meters / f.meters as missing_share,
        epoch(s.interval_start_ts) / ({{ var('interval_minutes') }} * 60)
        - row_number() over (partition by s.feeder_id order by s.interval_start_ts) as island
    from slot_missing as s
    inner join feeder_size as f on s.feeder_id = f.feeder_id
    where s.missing_meters >= {{ var('outage_missing_share') }} * f.meters
)

select
    'OUTAGE' as anomaly_type,
    null::varchar as meter_id,
    feeder_id,
    zone_id,
    min(interval_start_ts) as start_ts,
    max(interval_start_ts) + interval {{ var('interval_minutes') }} minute as end_ts,
    count(*) as intervals,
    'max_missing_share' as metric_name,
    round(max(missing_share), 3)::decimal(12, 3) as metric_value,
    {{ var('outage_missing_share') }}::decimal(12, 3) as threshold,
    max(missing_meters) as affected_meters,
    0::decimal(18, 4) as peak_kwh
from flagged
group by feeder_id, zone_id, island
having count(*) >= {{ var('outage_min_intervals') }}
