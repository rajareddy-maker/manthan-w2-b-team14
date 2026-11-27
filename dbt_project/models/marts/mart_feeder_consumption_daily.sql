-- Daily kWh per feeder with completeness (FR-09, dashboard "feeder consumption" tab).

select
    feeder_id,
    zone_id,
    interval_date_ist,
    sum(consumption_kwh)::decimal(18, 4) as consumption_kwh,
    count(*) as meters,
    count(*) filter (where intervals_received > 0) as meters_reporting,
    count(*) filter (where quality_flag = 'LOW_COMPLETENESS') as low_completeness_meters,
    round(100.0 * sum(intervals_received) / sum(intervals_expected), 2)::decimal(6, 2)
        as completeness_pct
from {{ ref('fct_consumption_daily') }}
group by feeder_id, zone_id, interval_date_ist
