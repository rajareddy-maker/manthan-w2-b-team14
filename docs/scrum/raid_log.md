# RAID Log

| ID | Type | Description | Owner | Status |
|---|---|---|---|---|
| R1 | Risk | Host RAM 14 GB; stack + IDE + browser may OOM containers | Raja Rao Reddy | Open — LITE profile, memory limits, other stacks stopped |
| R2 | Risk | Airflow 3 / dbt / GX Python dependency clash | Raja Rao Reddy | Open — dbt + GX in a separate venv inside the image |
| R3 | Risk | 5-hour time box too short for all 22 stories | Mahendra Umath | Open — Could stories dropped first; walking skeleton in S1 |
| R4 | Risk | DuckDB single-writer lock contention under Airflow | Shantanu Kale | Open — Airflow pool `duckdb` (1 slot) |
| R5 | Risk | Anomaly thresholds produce false positives | Rituja Kekatpure | Open — crafted histories + control meters; thresholds as dbt vars |
| A1 | Assumption | `energy` is a cumulative register | Mahendra Umath | Confirmed by PO |
| A2 | Assumption | Source timestamps are IST; buckets in Asia/Kolkata | Mahendra Umath | Confirmed by PO |
| A3 | Assumption | Demo uses 7 days of synthetic data | Mahendra Umath | Confirmed by PO |
| A4 | Assumption | Approval gates only at sprint reviews | Mahendra Umath | Confirmed by PO |
| I1 | Issue | Host port 5432 already used by a local Postgres | Raja Rao Reddy | Resolved — stack Postgres on host port 5433 |
| I2 | Issue | Installing uv via a piped install script was blocked by the sandbox policy | Raja Rao Reddy | Resolved — local tooling uses a stdlib venv on Python 3.14; runtime stays Py 3.13 in containers |
| I3 | Issue | `gh` CLI not installed; PRs cannot be opened from this session | Raja Rao Reddy | Open — local squash-merge per story; push needs PO OK |
| D1 | Dependency | Docker Hub reachable for Superset 6.1.0 / Postgres 16.16 tags | Raja Rao Reddy | Open |
| D2 | Dependency | Another local compose stack (`data-stack/airflow`) must stay stopped during demo | Raja Rao Reddy | Open |
