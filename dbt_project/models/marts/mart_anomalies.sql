-- One row per detected anomaly event: SPIKE, TAMPER, OUTAGE (FR-11..13, dashboard anomaly list).

with unioned as (
    select * from {{ ref('int_anomalies_spike_detected') }}
    union all by name
    select * from {{ ref('int_anomalies_tamper_detected') }}
    union all by name
    select * from {{ ref('int_anomalies_outage_detected') }}
)

select
    md5(
        concat_ws('|', anomaly_type, coalesce(meter_id, ''), feeder_id, start_ts::varchar)
    ) as anomaly_id,
    anomaly_type,
    meter_id,
    feeder_id,
    zone_id,
    start_ts,
    end_ts,
    cast(timezone('{{ var("tz") }}', start_ts) as date) as start_date_ist,
    intervals,
    metric_name,
    metric_value,
    threshold,
    affected_meters,
    peak_kwh
from unioned
