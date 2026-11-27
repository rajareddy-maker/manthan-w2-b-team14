# Environment setup and verification (Phase 1)

Host: Ubuntu 26.04 · Docker Desktop for Linux · 14 GB RAM (LITE profile).

## 1. System check
```bash
make system-check        # or: bash scripts/system_check.sh
```
Expected: every row `OK` (Java/pip may be `SKIP`), last line `RESULT: OK`.

## 2. Install missing prerequisites (Ubuntu)
```bash
sudo apt-get update && sudo apt-get install -y git make curl python3 python3-venv
# Docker Desktop for Linux: https://docs.docker.com/desktop/setup/install/linux/ubuntu/
systemctl --user start docker-desktop && docker info --format '{{.ServerVersion}}'
```
Verify: `docker compose version --short` gives a version ≥ 2.20.

**Memory:** set Docker Desktop to **6 GB** (Settings → Resources → Memory) on a 14–16 GB host, and close heavy apps. With 8 GB, systemd-oomd kills Docker Desktop under load (DEF-002).

## 3. Project setup and stack
```bash
make setup     # .env with random secrets, .venv, pinned deps, pre-commit
make up        # builds images, starts the stack, waits for every healthcheck
make smoke     # verification checklist below
```

## 4. Verification checklist
| # | Check | Command | Expected |
|---|---|---|---|
| 1 | Postgres accepts connections | `docker compose exec postgres pg_isready -U postgres -d warehouse` | `accepting connections` |
| 2 | Warehouse readable (read-only role) | part of `make smoke` | `warehouse initialised` |
| 3 | Airflow UI :8080 | `curl -fsS localhost:8080/api/v2/monitor/health` | JSON with `"status":"healthy"` |
| 4 | Hello DAG succeeds | `bash scripts/airflow_trigger_wait.sh hello_gridpulse` | `-> success` |
| 5 | dbt debug | `make dbt-debug` (or `LOCAL=1`) | `All checks passed!` |
| 6 | GX sample checkpoint | `make gx-validate` (or `LOCAL=1`) | `GX checkpoint PASSED` |
| 7 | Superset UI :8088 | `curl -fsS localhost:8088/health` | `OK` |
| 8 | Superset queries warehouse | part of `make smoke` | `superset->warehouse: warehouse initialised` |
| 9 | Kafka / Spark | — | SKIP (ADR-002) |

## 5. Troubleshooting (10 most common failures)
| Symptom | Cause | Fix |
|---|---|---|
| `failed to connect to the docker API … desktop/docker.sock` | Docker Desktop stopped or OOM-killed | `systemctl --user status docker-desktop`; lower its memory to 6 GB; close apps; `systemctl --user start docker-desktop` |
| `bind: address already in use` on 5432 | Host Postgres | We use host port **5433** (`POSTGRES_HOST_PORT` in .env) |
| Port 8080/8088 in use | Another stack (e.g. `~/Downloads/data-stack/airflow`) | `docker compose -p airflow down` in that folder, or change the port mapping |
| Permission denied writing `data/`, `logs` or `dbt_project/target` | `AIRFLOW_UID` ≠ host uid | `make env` writes `AIRFLOW_UID=$(id -u)`; for an old .env, edit it and `make down up` |
| `airflow-init` exits non-zero | Wrong DB password after .env changed post-init | `make clean` (drops volumes) then `make up` |
| Tasks stuck in `queued` | Scheduler unhealthy / execution API URL wrong | `make logs SERVICE=airflow-scheduler`; check `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` |
| Scheduler container restarts (exit 137) | Memory limit hit by DuckDB task | Lower `memory_limit` in dbt_project/profiles.yml, or raise `mem_limit` |
| Superset `No module named psycopg2` | Using the upstream lean image | Use the built `gridpulse-superset:0.1.0` image (`make build`) |
| `Database is locked` from DuckDB | Two writers at once | Tasks share Airflow pool `duckdb` (1 slot); stop local dbt while the DAG runs |
| `make up` hangs at `--wait` | A healthcheck never passes | `make ps` to find the unhealthy service, then `make logs SERVICE=<name>` |
