-- Voltage quality per feeder per IST day from v2 meters (FR-30, US-21).

select
    feeder_id,
    zone_id,
    interval_date_ist,
    min(voltage_v) as min_voltage_v,
    round(avg(voltage_v), 1)::decimal(6, 1) as avg_voltage_v,
    max(voltage_v) as max_voltage_v,
    count(distinct meter_id) as meters_reporting,
    count(*) as readings
from {{ ref('stg_meter__readings') }}
where voltage_v is not null
group by feeder_id, zone_id, interval_date_ist
