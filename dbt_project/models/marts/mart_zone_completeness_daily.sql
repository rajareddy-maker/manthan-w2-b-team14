-- Completeness % per zone per IST day (dashboard KPI, FR-18 / FR-22).
-- expected = every master meter x 96 slots; silent meters count as missing.

with zones as (
    select distinct
        zone_id,
        zone_name
    from {{ ref('feeder_zone') }}
)

select
    d.interval_date_ist,
    d.zone_id,
    z.zone_name,
    count(*) as meters_in_master,
    count(*) filter (where d.intervals_received > 0) as meters_reporting,
    sum(d.intervals_expected) as intervals_expected,
    sum(d.intervals_received) as intervals_received,
    round(100.0 * sum(d.intervals_received) / sum(d.intervals_expected), 2)::decimal(6, 2)
        as completeness_pct,
    count(*) filter (where d.quality_flag = 'LOW_COMPLETENESS') as low_completeness_meter_days
from {{ ref('fct_consumption_daily') }} as d
inner join zones as z on d.zone_id = z.zone_id
group by d.interval_date_ist, d.zone_id, z.zone_name
