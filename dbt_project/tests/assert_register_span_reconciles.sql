-- NFR-11: for every meter without a register_decrease, the sum of interval deltas in the window
-- equals (last register - register before the first delta) + rollovers × register_max, exactly.
with meter_stats as (
    select
        i.meter_id,
        sum(i.delta_kwh) as sum_delta_kwh,
        arg_max(i.register_kwh, i.interval_start_ts) filter (where i.delta_kwh is not null)
            as last_register_kwh,
        arg_min(i.prev_register_kwh, i.interval_start_ts) filter (where i.delta_kwh is not null)
            as first_prev_register_kwh,
        count(*) filter (
            where i.delta_kwh is not null and i.register_kwh < i.prev_register_kwh
        ) as rollovers,
        count(*) filter (where i.dq_flag = 'register_decrease') as decreases
    from {{ ref('int_meter_intervals') }} as i
    group by i.meter_id
)

select
    s.*,
    m.register_max_kwh
from meter_stats as s
inner join {{ ref('meter_master') }} as m on s.meter_id = m.meter_id
where
    s.decreases = 0
    and s.sum_delta_kwh is not null
    and s.sum_delta_kwh
    <> s.last_register_kwh - s.first_prev_register_kwh + s.rollovers * m.register_max_kwh
