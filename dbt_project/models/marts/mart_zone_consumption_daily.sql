-- Daily kWh per zone (FR-09).

with zones as (
    select distinct
        zone_id,
        zone_name
    from {{ ref('feeder_zone') }}
)

select
    d.zone_id,
    z.zone_name,
    d.interval_date_ist,
    sum(d.consumption_kwh)::decimal(18, 4) as consumption_kwh,
    count(*) as meters,
    count(*) filter (where d.intervals_received > 0) as meters_reporting
from {{ ref('fct_consumption_daily') }} as d
inner join zones as z on d.zone_id = z.zone_id
group by d.zone_id, z.zone_name, d.interval_date_ist
