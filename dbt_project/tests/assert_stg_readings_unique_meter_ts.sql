-- Dedup key (meter_id, reading_ts) must be unique after staging (FR-05).
select
    meter_id,
    reading_ts,
    count(*) as n
from {{ ref('stg_meter__readings') }}
group by meter_id, reading_ts
having count(*) > 1
