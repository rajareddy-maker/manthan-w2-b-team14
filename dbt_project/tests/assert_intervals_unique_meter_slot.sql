-- The grid has exactly one row per (meter_id, interval_start_ts).
select
    meter_id,
    interval_start_ts,
    count(*) as n
from {{ ref('int_meter_intervals') }}
group by meter_id, interval_start_ts
having count(*) > 1
