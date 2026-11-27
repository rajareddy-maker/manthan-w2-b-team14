-- Hourly kWh per meter (FR-08). Kept in the DuckDB lake for 13 months (ADR-003), not published.
-- A delta spanning a gap is counted in the hour of the reading that closes it.

select
    meter_id,
    feeder_id,
    zone_id,
    hour_start_ts,
    interval_date_ist,
    coalesce(sum(delta_kwh), 0)::decimal(18, 4) as consumption_kwh,
    count(reading_ts) as intervals_received,
    count(*) filter (where is_gap) as gap_intervals,
    count(*) filter (where dq_flag = 'register_decrease') as register_decrease_intervals
from {{ ref('int_meter_intervals') }}
group by meter_id, feeder_id, zone_id, hour_start_ts, interval_date_ist
