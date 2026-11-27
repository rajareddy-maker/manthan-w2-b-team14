-- Hourly kWh per feeder (FR-09).

select
    feeder_id,
    zone_id,
    hour_start_ts,
    interval_date_ist,
    sum(consumption_kwh)::decimal(18, 4) as consumption_kwh,
    count(*) filter (where intervals_received > 0) as meters_reporting,
    sum(intervals_received) as intervals_received,
    sum(gap_intervals) as gap_intervals
from {{ ref('fct_consumption_hourly') }}
group by feeder_id, zone_id, hour_start_ts, interval_date_ist
