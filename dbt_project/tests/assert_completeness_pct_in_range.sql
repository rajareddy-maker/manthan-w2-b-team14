-- Completeness can never exceed 100% or drop below 0% (dedup + grid snapping guarantee it).
select *
from {{ ref('mart_zone_completeness_daily') }}
where completeness_pct < 0 or completeness_pct > 100
