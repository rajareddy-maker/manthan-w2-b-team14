# Sprint 3: 27-Nov-2026 13:00 to 14:10 IST

**Sprint goal:** Stack running in Docker; marts published and charted; DQ gates, scheduled DAG with backfill, dashboard and test plan.
**Capacity:** 7.0 h **Committed:** 33 pts (US-14…US-17 + US-23) **Last velocity:** S2 23 pts (in review)

Host: Sagar's Windows 11 laptop.
- Docker Desktop 29.9.3 with the WSL2 backend; the VM has 7.65 GB.
- Docker Desktop is installed per user in `%LOCALAPPDATA%\Programs\DockerDesktop`.
- Every tool now runs from Docker: Airflow 3.3.2, Postgres 16.16 and Superset 6.1.0, plus the project venv with DuckDB, dbt and GX inside the Airflow image.
- The user's other compose project `airflow` (ports 8080/8088) was stopped, with its volumes kept, at the user's request.

## Sprint backlog
| Story ID | Title | Pts | Owner | Status |
|----------|-------|-----|-------|--------|
| US-04 (S0 carry) | Full stack in Docker Compose | 8 | Raja Rao Reddy | In review — AC1–AC3 met on Windows host |
| US-23 | Publish marts to Postgres + Superset chart | 7 | Raja Rao Reddy | In review — AC1–AC3 met |
| US-14 | DQ rules, quarantine and GX gates | 5 | Rituja Kekatpure | To do (DQ-1/2/3/4 already live in dbt) |
| US-15 | Daily Airflow DAG with retries, backfill, retention | 5 | Raja Rao Reddy | To do |
| US-16 | Superset network operations dashboard | 8 | Ishika Sadhwani | To do (first chart exists) |
| US-17 | Test plan, automated tests, published results | 8 | Ishika Sadhwani | To do (44 tests + evidence exist) |

## Sprint board
| To do | In progress | In review | Done | Blocked |
|-------|-------------|-----------|------|---------|
| US-14, US-15, US-16, US-17 | | US-04, US-23 | | |

## Daily standup log
| Date | Done since last | Plan today | Blockers |
|------|-----------------|------------|----------|
| 27-Nov 13:00 | S0, S1 approved; ADR-006 accepted; US-23 split; 10 branches pushed | Stack on Windows Docker; publish + chart | Ports 8080/8088 held by another stack (stopped with user OK) |
| 27-Nov 13:35 | Images built, stack healthy, smoke 9/9, publish 7/7, chart OK; full pipeline run inside Docker | US-15 DAG, US-14 GX gates | None |

## Sprint review
| Story ID | Demo evidence | Accepted? | Notes |
|----------|---------------|-----------|-------|
| US-04 | evidence/sprint_3/compose_up.txt, smoke_test.txt (9/9) | pending PO | Pinned images, healthchecks and memory limits; ~1.05 GB in use |
| US-23 | evidence/sprint_3/pipeline_in_docker.txt, superset_first_chart.txt, superset_chart_after_republish.txt | pending PO | 7/7 marts reconciled (445,848.1140 kWh); idempotent re-publish; chart reads via `bi_reader` |

## Impediments / RAID updates
| Type (R/A/I/D) | Description | Owner | Status |
|----------------|-------------|-------|--------|
| I | DEF-002/005/006 | Raja / Sagar | Closed |
| R | Bind-mounted repo (OneDrive folder) is ~4× slower in containers: generate 58 s vs 15 s natively | Sagar Kalthiya | Open — acceptable for a 7-day demo; consider moving `data/` to a named volume and outside OneDrive sync |
| A | GNU make not installed on Windows; Git Bash equivalents documented in docs/setup.md §2b | Sagar Kalthiya | Accepted |
