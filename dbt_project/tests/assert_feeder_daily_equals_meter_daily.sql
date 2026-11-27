-- Feeder and zone roll-ups must equal the sum of their meters (no double counting / loss).
with meter_total as (
    select sum(consumption_kwh) as kwh from {{ ref('fct_consumption_daily') }}
),

feeder_total as (
    select sum(consumption_kwh) as kwh from {{ ref('mart_feeder_consumption_daily') }}
),

zone_total as (
    select sum(consumption_kwh) as kwh from {{ ref('mart_zone_consumption_daily') }}
),

billing_total as (
    select sum(billed_kwh) as kwh from {{ ref('mart_billing_monthly') }}
)

select
    m.kwh as meter_kwh,
    f.kwh as feeder_kwh,
    z.kwh as zone_kwh,
    b.kwh as billed_kwh
from meter_total as m, feeder_total as f, zone_total as z, billing_total as b
where m.kwh <> f.kwh or m.kwh <> z.kwh or m.kwh <> b.kwh
