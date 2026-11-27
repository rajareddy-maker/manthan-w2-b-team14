# ADR-001: Airflow 3.3.2 (LocalExecutor) and the Python runtime

- **Status:** Accepted (Sprint 0, 27-Nov-2026) · **Deciders:** Mahendra Umath (PO), Raja Rao Reddy
- **Req IDs:** FR-16, FR-17, FR-27, NFR-10

## Context
The master prompt defaults to Airflow 2.x on Python 3.11. Constraints on the host:
- 14 GB RAM.
- Airflow 2.x has reached end of life.
- `apache/airflow:3.3.2` (Python 3.13) is already cached on the host.
- dbt-core 1.12 / Great Expectations 1.25 pin dependency ranges that conflict with Airflow's own.
- Installing `uv` on the host via a piped install script was refused by the sandbox policy.

## Options
1. Airflow 2.10 + Python 3.11 (master default). Needs a ~1.5 GB pull, and is EOL.
2. **Airflow 3.3.2, LocalExecutor, project venv inside the image.**
3. Airflow 3.3.2 with CeleryExecutor + Redis (like the host's other stack). About +1 GB RAM, with no benefit on one node.

## Decision
Option 2:
- Services: api-server, scheduler, dag-processor, init. No triggerer, because we use no deferrable operators.
- dbt, DuckDB, GX and the ingestion code run from `/opt/gridpulse-venv` via `BashOperator`, so the Airflow and project dependencies never clash.
- Container runtime: Python 3.13. Local tooling and tests use a stdlib venv on the host Python 3.14, with the same pinned packages (`constraints.txt`). CI runs Python 3.13.

## Consequences
- Supported Airflow release, and nothing to download for it.
- DAG code uses the Airflow 3 SDK (`airflow.sdk`).
- Tasks run inside the scheduler container (LocalExecutor), which is why the scheduler gets the largest memory limit (3 GB).
- Py 3.13 vs 3.14 drift risk is covered by CI on 3.13 plus `make smoke` inside the containers.
