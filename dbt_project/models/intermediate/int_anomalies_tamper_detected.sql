-- SUSPECTED TAMPER (FR-12): a meter's register is flat (0 kWh) for >= tamper_zero_intervals
-- consecutive intervals while >= tamper_peer_active_share of the other meters on its feeder
-- consumed energy in that same window. A zero delta that spans a gap counts for every slot it
-- covers (the register did not move across the gap). A whole-feeder zero period is not tamper.

with received as (
    select
        meter_id,
        feeder_id,
        zone_id,
        interval_start_ts,
        gap_intervals,
        delta_kwh = 0 as is_zero
    from {{ ref('int_meter_intervals') }}
    where delta_kwh is not null
),

runs as (
    select
        *,
        row_number() over (partition by meter_id order by interval_start_ts)
        - row_number() over (partition by meter_id, is_zero order by interval_start_ts) as run_id
    from received
),

zero_runs as (
    select
        meter_id,
        feeder_id,
        zone_id,
        min(interval_start_ts - to_minutes({{ var('interval_minutes') }} * gap_intervals))
            as start_ts,
        max(interval_start_ts) + interval {{ var('interval_minutes') }} minute as end_ts,
        sum(1 + gap_intervals) as zero_intervals
    from runs
    where is_zero
    group by meter_id, feeder_id, zone_id, run_id
    having sum(1 + gap_intervals) >= {{ var('tamper_zero_intervals') }}
),

feeder_size as (
    select
        feeder_id,
        count(*) as meters
    from {{ ref('meter_master') }}
    group by feeder_id
),

peer_usage as (
    select
        z.meter_id,
        z.start_ts,
        i.meter_id as peer_meter_id,
        coalesce(sum(i.delta_kwh), 0) as peer_kwh
    from zero_runs as z
    inner join {{ ref('int_meter_intervals') }} as i
        on
            z.feeder_id = i.feeder_id
            and z.meter_id <> i.meter_id
            and z.start_ts <= i.interval_start_ts
            and z.end_ts > i.interval_start_ts
    group by z.meter_id, z.start_ts, i.meter_id
),

peer_share as (
    select
        meter_id,
        start_ts,
        count(*) filter (where peer_kwh > 0) as active_peers
    from peer_usage
    group by meter_id, start_ts
)

select
    'TAMPER' as anomaly_type,
    z.meter_id,
    z.feeder_id,
    z.zone_id,
    z.start_ts,
    z.end_ts,
    z.zero_intervals as intervals,
    'active_peer_share' as metric_name,
    round(p.active_peers / (f.meters - 1), 3)::decimal(12, 3) as metric_value,
    {{ var('tamper_peer_active_share') }}::decimal(12, 3) as threshold,
    1 as affected_meters,
    0::decimal(18, 4) as peak_kwh
from zero_runs as z
inner join peer_share as p on z.meter_id = p.meter_id and z.start_ts = p.start_ts
inner join feeder_size as f on z.feeder_id = f.feeder_id
where p.active_peers >= {{ var('tamper_peer_active_share') }} * (f.meters - 1)
