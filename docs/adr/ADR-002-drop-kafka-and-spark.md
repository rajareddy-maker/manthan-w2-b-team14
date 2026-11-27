# ADR-002: No Kafka, no Spark (LITE profile)

- **Status:** Accepted (Sprint 0, 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Raja Rao Reddy
- **Req IDs:** FR-01, FR-02, NFR-01, NFR-03, NFR-10

## Context
- **Volume:** 480k events/day ≈ 100 MB JSON ≈ 15 MB Parquet per day; 43M events over 90 days.
- **Ingestion choice:** the PRD lets the team choose "files or Kafka".
- **Latency:** the PRD asks for daily orchestrated runs.
- **Host:** 14 GB RAM, so the master prompt mandates the LITE profile below 16 GB.

## Options
| Option | RAM | Benefit | Verdict |
|---|---|---|---|
| Kafka (KRaft) + UI | +1.5–2 GB | Intraday streaming, DLQ | Not needed for a daily SLA |
| Spark master + worker | +2–3 GB | Distributed compute | ~15 MB/day Parquet ≪ the ~10 GB/run threshold |
| **Files + DuckDB** | ~0.5 GB in-task | Columnar SQL on Hive-partitioned Parquet | **Chosen** |

## Decision
- Gateways land JSONL files under `data/landing/dt=YYYY-MM-DD/`.
- The extractor writes bronze Parquet partitioned `dt=/zone=`.
- DuckDB + dbt do all transforms. Kafka and Spark are not deployed.

## Consequences
- Lower RAM use and fewer moving parts. The 7-day demo processes in minutes.
- Without Kafka there is no consumer-offset DLQ. Rejected records go to a quarantine table with a reason code instead (FR-29).
- Re-entry path: each landing line is one self-describing JSON event (Kafka-message compatible), so a Kafka producer/consumer can be added later without changing bronze or later layers.
- Smoke-test rows for Kafka and Spark are reported as SKIP (by design).
