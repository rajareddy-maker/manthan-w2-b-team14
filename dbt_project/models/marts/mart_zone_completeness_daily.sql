-- Completeness % per zone per IST day (dashboard KPI, FR-18 / FR-22).
-- expected = meters in master x 96; received = distinct valid on-grid intervals.

with meters as (
    select
        z.zone_id,
        z.zone_name,
        count(m.meter_id) as meters_in_master
    from {{ ref('feeder_zone') }} as z
    inner join {{ ref('meter_master') }} as m on z.feeder_id = m.feeder_id
    group by z.zone_id, z.zone_name
),

per_meter_day as (
    select
        zone_id,
        interval_date_ist,
        meter_id,
        count(*) as intervals_received
    from {{ ref('stg_meter__readings') }}
    group by zone_id, interval_date_ist, meter_id
),

per_zone_day as (
    select
        zone_id,
        interval_date_ist,
        count(*) as meters_reporting,
        sum(intervals_received) as intervals_received,
        count(*) filter (
            where intervals_received
            < {{ var('intervals_per_day') }} * {{ var('completeness_threshold') }}
        ) as low_completeness_reporting_meters
    from per_meter_day
    group by zone_id, interval_date_ist
)

select
    d.interval_date_ist,
    m.zone_id,
    m.zone_name,
    m.meters_in_master,
    d.meters_reporting,
    m.meters_in_master * {{ var('intervals_per_day') }} as intervals_expected,
    d.intervals_received,
    round(
        100.0 * d.intervals_received / (m.meters_in_master * {{ var('intervals_per_day') }}), 2
    )::decimal(6, 2) as completeness_pct,
    d.low_completeness_reporting_meters
    + (m.meters_in_master - d.meters_reporting) as low_completeness_meter_days
from per_zone_day as d
inner join meters as m on d.zone_id = m.zone_id
