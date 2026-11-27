-- Interval consumption can never be negative: decreases are either ROLLOVER-corrected or NULL.
select *
from {{ ref('int_meter_intervals') }}
where delta_kwh < 0
