-- Valid, de-duplicated readings: one row per (meter_id, reading_ts), earliest ingest kept.

select
    meter_id,
    feeder_id,
    zone_id,
    reading_ts,
    interval_start_ts,
    interval_date_ist,
    register_kwh,
    status,
    voltage_v,
    firmware_version,
    schema_version,
    snap_seconds,
    source_file,
    line_no,
    file_arrival_ts,
    ingested_at,
    landing_date_ist
from {{ ref('stg_meter__readings_validated') }}
where reject_reason is null and dup_rank = 1
