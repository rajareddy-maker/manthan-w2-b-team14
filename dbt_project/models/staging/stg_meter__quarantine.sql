-- Rejected bronze rows with their reason code and original payload (FR-29). Replayable.

select
    reject_reason,
    meter_id,
    source_reading_ts,
    source_energy,
    source_unit,
    schema_version,
    raw_payload,
    source_file,
    line_no,
    file_arrival_ts,
    ingested_at,
    landing_date_ist
from {{ ref('stg_meter__readings_validated') }}
where reject_reason is not null
