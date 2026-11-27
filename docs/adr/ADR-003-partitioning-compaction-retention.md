# ADR-003: Partitioning, compaction and retention of the time-series lake

- **Status:** Accepted (Sprint 1 review, 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Sagar Kalthiya
- **Req IDs:** FR-14, FR-15, NFR-01, NFR-06, NFR-07

## Context
- 480k readings/day arrive as 144 hourly gateway files (6 zones × 24 h), plus re-sent and late files.
- Bronze must stay raw and replayable. A re-run of any date must give identical results (NFR-07).
- Measured on the 7-day demo set (5,000 meters): 3.39M lines, **397 MB JSONL → 38 MB zstd Parquet** (≈ 4.8 MB/day).
- Query patterns:
  - Ingestion and DQ read "everything that arrived on day X".
  - Normalisation reads a 3-day lookback window plus one day of context.
  - Ops filter by zone.

## Options
| # | Bronze partition key | Pros | Cons |
|---|---|---|---|
| A | **`dt` = landing arrival date (IST) / `zone` = gateway zone** | Append-only. A late file never touches an older partition. Replaying one arrival date is a single atomic directory swap. | A query by reading date must scan arrival dates `[D, D+3]` (4 days, ~20 MB). |
| B | `dt` = reading date / `zone` | Direct pruning by reading date | Late files rewrite old partitions, so bronze is no longer append-only. Idempotency needs merge logic. |
| C | `meter_id` hash buckets | Fast per-meter history | Thousands of tiny files. No time pruning, so retention cannot drop whole directories. |

## Decision
1. **Partitioning — option A.**
   - Layout: `data/lake/bronze/dt=YYYY-MM-DD/zone=Zxx/part-0.parquet`, where `dt` is the IST date the file arrived.
   - Silver and gold (DuckDB tables) are keyed by reading date (`interval_date_ist`, the IST date of the interval a reading closes), so business queries prune on reading time.
2. **Compaction.** The extractor rebuilds a whole `dt` partition in a temp directory, then swaps it in atomically.
   - Each `dt/zone` holds **exactly one** zstd Parquet file: 144 small files/day become 6.
   - `compact_partition()` (and `python -m ingestion.extractors.landing_to_bronze --compact`) merges any partition with more than one file, for example after a manual drop-in.
3. **Retention** (implemented by the retention task, US-15; every drop is logged to `ops`):

   | Data | Keep | Reason |
   |---|---|---|
   | Landing JSONL + bronze | **30 days** by `dt` | Covers the 3-day lookback, a month of backfill or replay, and the billing-dispute window for the current cycle. ≈ 150 MB. |
   | Hourly per-meter consumption (DuckDB/Parquet) | **13 months** by reading date | Same-month-last-year comparison for billing disputes and load planning. ≈ 47M rows/13 mo, kept in the lake, not Postgres. |
   | Hourly per-feeder/zone, daily and monthly marts (Postgres) | Indefinitely | Small: hourly feeder rows are ~190k/13 mo, and daily/monthly are smaller still. |
   | Quarantine | 30 days | Same as raw, since it is the raw record of rejected rows |

## Evidence (US-06 AC3)
Measured with `docs/evidence/sprint_1/bronze_checks.txt` on 48 partitions:

| Predicted query | Files scanned | Rows | Time |
|---|---|---|---|
| Full scan | 48/48 | 3,392,136 | 133 ms |
| One arrival day (`dt`) | **6/48** | 482,931 | 26 ms |
| One day + one zone (`dt`, `zone`) | **1/48** | 68,841 | 21 ms |

## Consequences
- Bronze is truly append-only: a partition is only ever replaced by a replay of the same landing files. Every rerun is idempotent (verified: same row count and payload hash).
- Normalisation must read arrival dates `[D−3, D+1]` to cover reading dates `[D−3, D]` (ADR-004).
- The 30-day raw retention bounds how far back a backfill can go. Anything older must come from an archived landing copy (runbook).
