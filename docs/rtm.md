# Requirements Traceability Matrix (RTM)

Status: **skeleton (Sprint 0)**. Design/Code/Test columns are filled as stories complete. Test status: ⬜ not run · ✅ pass · ❌ fail.

| Req ID | Story | Design (LLD section) | Code (repo path) | Test case(s) | Status |
|---|---|---|---|---|---|
| FR-01 | US-07, US-08 | LLD §3.1 source contract v1 | ingestion/extractors/ | TC-ING-01 | ⬜ |
| FR-02 | US-07, US-08 | LLD §3.1 source contract v2 | ingestion/extractors/ | TC-ING-02 | ⬜ |
| FR-03 | US-08 | LLD §2 bronze table | ingestion/extractors/ | TC-ING-03 | ⬜ |
| FR-04 | US-10 | LLD §2 S2T mapping | dbt_project/models/staging/ | TC-UNIT-01 (unit conversion) | ⬜ |
| FR-05 | US-10 | LLD §2 dedup rule | dbt_project/models/staging/ | TC-DUP-01 | ⬜ |
| FR-06 | US-10 | LLD §2 ordering | dbt_project/models/intermediate/ | TC-ORD-01 | ⬜ |
| FR-07 | US-11 | LLD §2 int_meter_intervals | dbt_project/models/intermediate/ | TC-GAP-01 (gap detection) | ⬜ |
| FR-08 | US-12 | LLD §2 fct_consumption_hourly/daily | dbt_project/models/marts/ | TC-REC-01 (reconcile to raw) | ⬜ |
| FR-09 | US-12 | LLD §2 mart_feeder/zone_daily | dbt_project/models/marts/ | TC-REC-02 | ⬜ |
| FR-10 | US-12 | LLD §2 mart_billing_monthly | dbt_project/models/marts/ | TC-BILL-01 | ⬜ |
| FR-11 | US-13 | LLD §1 anomaly models | dbt_project/models/marts/ | TC-ANO-01 (spike) | ⬜ |
| FR-12 | US-13 | LLD §1 anomaly models | dbt_project/models/marts/ | TC-ANO-02 (tamper) | ⬜ |
| FR-13 | US-13 | LLD §1 anomaly models | dbt_project/models/marts/ | TC-ANO-03 (outage) | ⬜ |
| FR-14 | US-08, US-06 | ADR-003 | ingestion/extractors/compaction | TC-STO-01 | ⬜ |
| FR-15 | US-15, US-06 | ADR-003 | ingestion/extractors/retention | TC-STO-02 | ⬜ |
| FR-16 | US-15 | LLD §1 DAG design | airflow/dags/ | TC-ORC-01 | ⬜ |
| FR-17 | US-15 | LLD §1 backfill | airflow/dags/ | TC-ORC-02 | ⬜ |
| FR-18 | US-16 | LLD §3 Superset contract | superset/ | TC-UAT-18 | ⬜ |
| FR-19 | US-14 | LLD DQ design | dbt tests + data_quality/gx | TC-DQ-01 | ⬜ |
| FR-20 | US-14 | LLD DQ design | dbt tests + data_quality/gx | TC-DQ-02 | ⬜ |
| FR-21 | US-14 | LLD DQ design | dbt_project/tests/ | TC-DQ-03 | ⬜ |
| FR-22 | US-14 | LLD DQ design | dbt_project/models/marts/ | TC-DQ-04 | ⬜ |
| FR-23 | US-07 | LLD §3.1 | ingestion/generator/ | TC-GEN-01 | ⬜ |
| FR-24 | US-19 | LLD monitoring | ops schema + DAG callbacks | TC-OPS-01 | ⬜ |
| FR-25 | US-19 | LLD monitoring | airflow/dags/ alert task | TC-OPS-02 | ⬜ |
| FR-26 | US-20 | docs/runbook.md | scripts/ | TC-OPS-03 (backfill + rollback drill) | ⬜ |
| FR-27 | US-04, US-18 | docs/architecture.md | docker-compose.yml, .github/workflows | TC-DEP-01 (clean start) | ⬜ |
| FR-28 | US-06 | ADR-004, ADR-005 | — | review | ⬜ |
| FR-29 | US-14 | LLD DQ design | dbt_project/models/ quarantine | TC-DQ-05 | ⬜ |
| FR-30 | US-21 | LLD §2 | dbt_project/models/marts/ | TC-UAT-30 | ⬜ |
| NFR-03 | US-17 | — | — | TC-PERF-01 | ⬜ |
| NFR-07 | US-08, US-15 | ADR-004 | — | TC-IDEM-01 | ⬜ |
| NFR-11 | US-12 | — | — | TC-REC-01 | ⬜ |
