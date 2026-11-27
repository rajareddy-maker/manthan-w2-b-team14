# ADR-005: Schema evolution (v1 → v2 → future)

- **Status:** Proposed (Sprint 1, 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Sagar Kalthiya
- **Req IDs:** FR-01, FR-02, FR-03, FR-04, FR-28

## Context
Two firmware generations report differently.

| | v1 (≈60% of meters) | v2 (≈40%) |
|---|---|---|
| Version marker | none | `"schema_version": 2` |
| Energy | `energy_wh` (integer Wh, cumulative) | `energy` + `unit` ∈ {`Wh`, `kWh`} |
| Extra fields | — | `voltage`, `firmware_version` |
| Timestamp | ISO-8601 IST, sometimes naive | ISO-8601 with `+05:30` |

- Both versions arrive mixed in the same gateway file.
- A v3 is expected as firmware rolls out.

## Options
| # | Approach | Verdict |
|---|---|---|
| A | Schema registry (Avro/Protobuf, Confluent) | Needs Kafka (ADR-002). Gateways send JSON anyway. |
| B | One bronze table per version | Every downstream model has to union N tables. A new version breaks ingestion until code ships. |
| C | **Schema-on-read: bronze keeps the raw payload; staging maps each version to one canonical contract** | **Chosen** |

## Decision
1. **Bronze is schema-agnostic.**
   - It stores `raw_payload` (string) plus `schema_version` and `meter_id` extracted for lineage.
   - Version detection: an explicit `schema_version` field wins; otherwise the presence of `energy_wh` ⇒ v1; otherwise `NULL`.
   - A new firmware version can never break ingestion.
2. **Canonical staging contract** (`stg_meter__readings`):

   | Column | Type | Rule |
   |---|---|---|
   | `meter_id` | varchar | |
   | `reading_ts` | timestamptz | Naive values are read as IST |
   | `register_kwh` | decimal(18,4) | v1: `energy_wh / 1000`; v2: `energy / 1000` if `unit = 'Wh'` else `energy` |
   | `status` | varchar | |
   | `voltage_v` | decimal(6,1) | NULL for v1 |
   | `firmware_version` | varchar | NULL for v1 |
   | `schema_version` | smallint | |

   - Lineage columns are kept alongside: `source_file`, `line_no`, `ingested_at`, `file_arrival_ts`.
   - Each version is one CTE, combined with `union all by name`.
3. **Unknown versions or units are quarantined, never guessed.** Reason codes: `unknown_schema` (version NULL or not handled), `unknown_unit`, `invalid_json`. Quarantine keeps the raw payload so the row can be replayed once support is added.
4. **Adding a version (v3) checklist:**
   - add one CTE in staging;
   - extend the `accepted_values` test on `schema_version`;
   - add a unit fixture and test;
   - replay the affected bronze dates with backfill. Bronze already holds the data.
5. **Contract tests:**
   - dbt `accepted_values` on `schema_version` and `unit`;
   - `not_null` on canonical columns;
   - a GX expectation that `register_kwh ≥ 0`;
   - a unit test that 1500 Wh (v1) = 1500 Wh (v2) = 1.5 kWh (v2) → 1.5000 kWh.

## Consequences
- The only per-version code lives in one staging model. Silver and gold never see a version difference except the nullable v2 fields.
- Unhandled data is visible (quarantine count by reason on the pipeline-health tab), not silently dropped.
- JSON parsing happens in staging on every run. At ~2.4M rows per 5-day window this costs seconds in DuckDB.
