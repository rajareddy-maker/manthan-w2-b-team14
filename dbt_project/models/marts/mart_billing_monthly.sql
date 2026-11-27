-- Billing-ready kWh per meter per IST month (FR-10). DECIMAL(18,4), never FLOAT.
-- is_partial_month: the data window does not cover every day of the month (do not bill yet).

select
    date_trunc('month', interval_date_ist)::date as billing_month_ist,
    meter_id,
    feeder_id,
    zone_id,
    sum(consumption_kwh)::decimal(18, 4) as billed_kwh,
    count(*) as days_covered,
    sum(intervals_expected) as intervals_expected,
    sum(intervals_received) as intervals_received,
    sum(gap_intervals) as gap_intervals,
    sum(register_decrease_intervals) as register_decrease_intervals,
    count(*) filter (where quality_flag = 'LOW_COMPLETENESS') as low_completeness_days,
    round(100.0 * sum(intervals_received) / sum(intervals_expected), 2)::decimal(6, 2)
        as completeness_pct,
    count(*) < day(last_day(min(interval_date_ist))) as is_partial_month,
    case
        when sum(register_decrease_intervals) > 0 then 'REGISTER_DECREASE'
        when sum(intervals_received) < sum(intervals_expected) * {{ var('completeness_threshold') }}
            then 'LOW_COMPLETENESS'
        else 'OK'
    end as quality_flag
from {{ ref('fct_consumption_daily') }}
group by date_trunc('month', interval_date_ist)::date, meter_id, feeder_id, zone_id
