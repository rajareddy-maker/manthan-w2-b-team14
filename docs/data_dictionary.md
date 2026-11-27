# GridPulse — Data Dictionary

Generated from the DuckDB warehouse (`information_schema`) and dbt `schema.yml` descriptions on 27-Nov-2026.
Regenerate after model changes. Units: every `_kwh` column is kWh DECIMAL(18,4). `_ts` = TIMESTAMPTZ; `_date_ist` = IST calendar date.
Published = copied to Postgres `warehouse.marts` (Superset reads these via `bi_reader`).

## Bronze (Parquet, `data/lake/bronze/dt=/zone=/part-0.parquet`)
| Column | Type | Description |
|---|---|---|
| raw_payload | VARCHAR | Exact landed JSON line (never modified) |
| is_valid_json | BOOLEAN | Line parses as JSON |
| schema_version | SMALLINT | 2 if explicit, 1 if `energy_wh` present, else NULL |
| meter_id | VARCHAR | Extracted for lineage; NULL if invalid JSON |
| source_file | VARCHAR | `dt=…/gw-<zone>-<YYYYMMDD>-<HH>[-rN].jsonl` |
| line_no | INTEGER | Line number in source file |
| file_arrival_ts | TIMESTAMPTZ | Gateway file arrival (mtime) |
| ingested_at | TIMESTAMPTZ | Extractor run time |
| dt / zone | hive keys | IST arrival date / gateway zone |

## Seeds (reference)

### `feeder_zone`

Feeder to zone mapping with zone display names.

| Column | Type | Description |
|---|---|---|
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| zone_name | VARCHAR |  |

### `meter_master`

Meter master (DQ rule 1 reference). One row per installed meter with its feeder, zone, firmware schema version, reporting unit and register rollover point. Written by the generator.

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| schema_version | SMALLINT |  |
| unit | VARCHAR |  |
| install_date | DATE |  |
| register_max_kwh | DECIMAL(18,4) |  |
## Intermediate (silver)

### `int_anomalies_outage_detected`

OUTAGE (FR-13): >= 30% of a feeder's meters missing the same interval for >= 2 consecutive intervals; one event per contiguous run.

| Column | Type | Description |
|---|---|---|
| anomaly_type | VARCHAR |  |
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| start_ts | TIMESTAMP WITH TIME ZONE |  |
| end_ts | TIMESTAMP WITH TIME ZONE |  |
| intervals | BIGINT |  |
| metric_name | VARCHAR |  |
| metric_value | DECIMAL(12,3) |  |
| threshold | DECIMAL(12,3) |  |
| affected_meters | BIGINT |  |
| peak_kwh | DECIMAL(18,4) |  |

### `int_anomalies_spike_detected`

SPIKE events (FR-11, ADR-006): z > spike_z_threshold vs the meter's trailing 30 days (>= 96 clean points) and kWh >= spike_min_multiple × trailing mean; consecutive intervals merged into one event.

| Column | Type | Description |
|---|---|---|
| anomaly_type | VARCHAR |  |
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| start_ts | TIMESTAMP WITH TIME ZONE |  |
| end_ts | TIMESTAMP WITH TIME ZONE |  |
| intervals | BIGINT |  |
| metric_name | VARCHAR |  |
| metric_value | DECIMAL(12,3) |  |
| threshold | DECIMAL(12,3) |  |
| affected_meters | INTEGER |  |
| peak_kwh | DECIMAL(18,4) |  |

### `int_anomalies_tamper_detected`

Suspected TAMPER (FR-12): register flat for >= 192 intervals while >= 70% of feeder peers consumed energy in the same window.

| Column | Type | Description |
|---|---|---|
| anomaly_type | VARCHAR |  |
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| start_ts | TIMESTAMP WITH TIME ZONE |  |
| end_ts | TIMESTAMP WITH TIME ZONE |  |
| intervals | HUGEINT |  |
| metric_name | VARCHAR |  |
| metric_value | DECIMAL(12,3) |  |
| threshold | DECIMAL(12,3) |  |
| affected_meters | INTEGER |  |
| peak_kwh | DECIMAL(18,4) |  |

### `int_meter_intervals`

Meter × 15-min grid for the window (every meter in the master, every slot). is_gap marks slots no valid reading closes; never filled. delta_kwh = register delta (ROLLOVER-aware); NULL with dq_flag = register_decrease when the register drops without ROLLOVER. A delta that spans missing slots is kept once on the closing slot with gap_intervals = n.

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| interval_start_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_end_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_date_ist | DATE |  |
| hour_start_ts | TIMESTAMP WITH TIME ZONE |  |
| reading_ts | TIMESTAMP WITH TIME ZONE |  |
| register_kwh | DECIMAL(18,4) |  |
| prev_register_kwh | DECIMAL(18,4) |  |
| status | VARCHAR |  |
| is_gap | BOOLEAN |  |
| gap_intervals | INTEGER |  |
| delta_kwh | DECIMAL(18,4) |  |
| dq_flag | VARCHAR |  |
## Marts (gold)

### `fct_consumption_daily` — published

Daily kWh per meter with completeness % and quality_flag = LOW_COMPLETENESS when fewer than 90% of the 96 intervals were received (DQ-4, FR-22).

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| interval_date_ist | DATE |  |
| consumption_kwh | DECIMAL(18,4) |  |
| intervals_expected | BIGINT |  |
| intervals_received | BIGINT |  |
| gap_intervals | BIGINT |  |
| register_decrease_intervals | BIGINT |  |
| completeness_pct | DECIMAL(6,2) |  |
| quality_flag | VARCHAR |  |

### `fct_consumption_hourly`

Hourly kWh per meter from register deltas (FR-08). A delta spanning gaps lands in the hour of its closing reading. Lake-only (13-month retention, ADR-003).

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| hour_start_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_date_ist | DATE |  |
| consumption_kwh | DECIMAL(18,4) |  |
| intervals_received | BIGINT |  |
| gap_intervals | BIGINT |  |
| register_decrease_intervals | BIGINT |  |

### `mart_anomalies` — published

One row per anomaly event (SPIKE / TAMPER / OUTAGE) with window, metric vs threshold and affected meters. meter_id is NULL for OUTAGE (feeder-level). Dashboard anomaly list (FR-18).

| Column | Type | Description |
|---|---|---|
| anomaly_id | VARCHAR |  |
| anomaly_type | VARCHAR |  |
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| start_ts | TIMESTAMP WITH TIME ZONE |  |
| end_ts | TIMESTAMP WITH TIME ZONE |  |
| start_date_ist | DATE |  |
| intervals | HUGEINT |  |
| metric_name | VARCHAR |  |
| metric_value | DECIMAL(12,3) |  |
| threshold | DECIMAL(12,3) |  |
| affected_meters | BIGINT |  |
| peak_kwh | DECIMAL(18,4) |  |

### `mart_billing_monthly` — published

Billing-ready kWh per meter per IST month (FR-10): billed_kwh DECIMAL(18,4), completeness, gap intervals and quality_flag (REGISTER_DECREASE > LOW_COMPLETENESS > OK). is_partial_month = the data window does not cover the whole month.

| Column | Type | Description |
|---|---|---|
| billing_month_ist | DATE |  |
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| billed_kwh | DECIMAL(18,4) |  |
| days_covered | BIGINT |  |
| intervals_expected | HUGEINT |  |
| intervals_received | HUGEINT |  |
| gap_intervals | HUGEINT |  |
| register_decrease_intervals | HUGEINT |  |
| low_completeness_days | BIGINT |  |
| completeness_pct | DECIMAL(6,2) |  |
| is_partial_month | BOOLEAN |  |
| quality_flag | VARCHAR |  |

### `mart_feeder_consumption_daily` — published

Daily kWh, completeness and low-completeness meters per feeder (FR-09, FR-18).

| Column | Type | Description |
|---|---|---|
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| interval_date_ist | DATE |  |
| consumption_kwh | DECIMAL(18,4) |  |
| meters | BIGINT |  |
| meters_reporting | BIGINT |  |
| low_completeness_meters | BIGINT |  |
| completeness_pct | DECIMAL(6,2) |  |

### `mart_feeder_consumption_hourly` — published

Hourly kWh and reporting meters per feeder (FR-09).

| Column | Type | Description |
|---|---|---|
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| hour_start_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_date_ist | DATE |  |
| consumption_kwh | DECIMAL(18,4) |  |
| meters_reporting | BIGINT |  |
| intervals_received | HUGEINT |  |
| gap_intervals | HUGEINT |  |

### `mart_feeder_voltage_daily` — published

Min / avg / max voltage and reporting v2 meters per feeder per IST day (FR-30).

| Column | Type | Description |
|---|---|---|
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| interval_date_ist | DATE |  |
| min_voltage_v | DECIMAL(6,1) |  |
| avg_voltage_v | DECIMAL(6,1) |  |
| max_voltage_v | DECIMAL(6,1) |  |
| meters_reporting | BIGINT |  |
| readings | BIGINT |  |

### `mart_zone_completeness_daily` — published

Completeness % per zone per IST day over every master meter × 96 slots (silent meters count as missing); low_completeness_meter_days = meters below 90% (FR-18, FR-22).

| Column | Type | Description |
|---|---|---|
| interval_date_ist | DATE |  |
| zone_id | VARCHAR |  |
| zone_name | VARCHAR |  |
| meters_in_master | BIGINT |  |
| meters_reporting | BIGINT |  |
| intervals_expected | HUGEINT |  |
| intervals_received | HUGEINT |  |
| completeness_pct | DECIMAL(6,2) |  |
| low_completeness_meter_days | BIGINT |  |

### `mart_zone_consumption_daily` — published

Daily kWh per zone (FR-09).

| Column | Type | Description |
|---|---|---|
| zone_id | VARCHAR |  |
| zone_name | VARCHAR |  |
| interval_date_ist | DATE |  |
| consumption_kwh | DECIMAL(18,4) |  |
| meters | BIGINT |  |
| meters_reporting | BIGINT |  |
## Staging (silver)

### `stg_meter__quarantine`

Rejected rows with reason code and original payload (FR-29), replayable.

| Column | Type | Description |
|---|---|---|
| reject_reason | VARCHAR |  |
| meter_id | VARCHAR |  |
| source_reading_ts | TIMESTAMP WITH TIME ZONE |  |
| source_energy | DECIMAL(18,4) |  |
| source_unit | VARCHAR |  |
| schema_version | SMALLINT |  |
| raw_payload | VARCHAR |  |
| source_file | VARCHAR |  |
| line_no | INTEGER |  |
| file_arrival_ts | TIMESTAMP WITH TIME ZONE |  |
| ingested_at | TIMESTAMP WITH TIME ZONE |  |
| landing_date_ist | DATE |  |

### `stg_meter__readings`

Valid, de-duplicated readings. One row per (meter_id, reading_ts); register in kWh (DECIMAL(18,4)); reading_ts is on the 15-min grid; interval_date_ist is the IST date of the interval the reading closes (reading at 00:00 belongs to the previous day).

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| reading_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_start_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_date_ist | DATE |  |
| register_kwh | DECIMAL(18,4) |  |
| status | VARCHAR |  |
| voltage_v | DECIMAL(6,1) |  |
| firmware_version | VARCHAR |  |
| schema_version | SMALLINT |  |
| snap_seconds | BIGINT |  |
| source_file | VARCHAR |  |
| line_no | INTEGER |  |
| file_arrival_ts | TIMESTAMP WITH TIME ZONE |  |
| ingested_at | TIMESTAMP WITH TIME ZONE |  |
| landing_date_ist | DATE |  |

### `stg_meter__readings_validated`

Every bronze row mapped to the canonical reading contract (ADR-005): kWh register, IST timestamp snapped to the 15-min grid (±2 min), reject_reason (NULL = valid) and dup_rank among valid rows (1 = kept: earliest ingested_at, then arrival, file, line).

| Column | Type | Description |
|---|---|---|
| meter_id | VARCHAR |  |
| feeder_id | VARCHAR |  |
| zone_id | VARCHAR |  |
| reading_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_start_ts | TIMESTAMP WITH TIME ZONE |  |
| interval_date_ist | DATE |  |
| register_kwh | DECIMAL(18,4) |  |
| status | VARCHAR |  |
| voltage_v | DECIMAL(6,1) |  |
| firmware_version | VARCHAR |  |
| schema_version | SMALLINT |  |
| source_reading_ts | TIMESTAMP WITH TIME ZONE |  |
| source_energy | DECIMAL(18,4) |  |
| source_unit | VARCHAR |  |
| snap_seconds | BIGINT |  |
| reject_reason | VARCHAR | NULL for valid rows, otherwise the first failed rule. |
| dup_rank | BIGINT |  |
| raw_payload | VARCHAR |  |
| source_file | VARCHAR |  |
| line_no | INTEGER |  |
| file_arrival_ts | TIMESTAMP WITH TIME ZONE |  |
| ingested_at | TIMESTAMP WITH TIME ZONE |  |
| landing_date_ist | DATE |  |
| gateway_zone | VARCHAR |  |

## Ops (Postgres `warehouse.ops`, written by `ingestion/ops/metrics.py`)
| Table | Columns |
|---|---|
| pipeline_runs | run_id (PK), dag_id, logical_date_ist, started_ts, finished_ts, status, bronze_rows, quarantined_rows, duplicate_rate_pct, completeness_pct, ingest_lag_p50_min, ingest_lag_p95_min, late_beyond_window_events, duration_s |
| alerts | alert_id (PK), raised_ts, run_id, severity, alert_type (completeness_drop / late_beyond_window), scope, message |
