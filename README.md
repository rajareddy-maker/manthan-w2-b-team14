# GridPulse — Smart Meter Telemetry Platform

Team 14 · Track B · NucleusTeq Indore · 27-Nov-2026

GridPulse ingests smart-meter telemetry in two schema versions and normalises it:
- converts all readings to kWh, in IST;
- removes duplicates and orders readings;
- marks missing intervals as gaps instead of filling them.

From that it builds billing-ready consumption tables and flags spike, suspected-tamper and outage anomalies. Results appear on a Superset dashboard.

## Quick start
```bash
make demo
```
`make demo` does the following:
1. Creates `.env` with random secrets.
2. Builds and starts the stack (Postgres, Airflow 3, Superset) and waits for the healthchecks.
3. Verifies every service.
4. Runs the pipeline.
5. Prints the URLs and logins: Airflow http://localhost:8080, Superset http://localhost:8088.

Prerequisites: run `make system-check`; see [docs/setup.md](docs/setup.md). Docker Desktop needs ≥ 6 GB of memory.

## Status
Sprint 0 (inception + environment). See [docs/PROGRESS.md](docs/PROGRESS.md).

## Docs
[Ideation](docs/ideation.md) · [Requirements](docs/requirements.md) · [RTM](docs/rtm.md) · [Backlog](docs/scrum/product_backlog.md) · [ADRs](docs/adr/) · [Setup & troubleshooting](docs/setup.md) · [Test results](docs/test_results.md)
