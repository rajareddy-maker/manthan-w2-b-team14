# GridPulse — Artifacts Checklist (Module 2 evaluation: "Artifacts to Deliver")

Status as of 27-Nov-2026 · `main` @ `dc5b11f` on GitHub (`rajareddy-maker/manthan-w2-b-team14`)
✅ ready · 🟡 partly ready · ❌ pending

## The ten artifacts
| # | Artifact | Expected | Where | Status | Gap / next step |
|---|---|---|---|---|---|
| 1 | Presentation | Story of the build and key topics | — | ❌ Pending | Build the deck from `docs/completion_report.md`, `docs/architecture.md`, the ADRs and the evidence below |
| 2 | Code base | Repository, README, one-command run | GitHub `main`; `README.md`; `scripts/demo.sh` / `make demo` | ✅ Ready | Demo ran successfully in 658 s. CI/CD files are local only (need gh `workflow` scope). |
| 3 | Test plan | Scope, risks, entry and exit criteria | `docs/test_plan.md` | ✅ Ready | — |
| 4 | Test results | Executed cases, defects and evidence | `docs/test_results.md` (execution summary, exit criteria, DEF-001…014) + `docs/evidence/` | ✅ Ready | Performance (10×) row still "not run" |
| 5 | UI designs | Wireframes and final screens | Final screens: `docs/demo/frames/` (4 dashboard tabs, Airflow DAGs/graph/runs, repo); dashboard as code `scripts/superset_dashboard.py` | 🟡 Partial | Final screens ✅; wireframes still pending |
| 6 | Stories (Excel) | Backlog with acceptance criteria | `docs/scrum/product_backlog.xlsx` (+ `.md`) | ✅ Ready | 23 stories / 111 pts; 96 accepted |
| 7 | Application demo | Running app, five-minute walkthrough | `docs/demo/gridpulse_demo.mp4` (4 min 33 s, 1080p, voiceover); `docs/demo/demo_script.md`; `docs/demo/gridpulse_walkthrough.gif` | ✅ Ready | Rebuild: `python docs/demo/build_video.py` |
| 8 | Ideation document | Problem, options, chosen approach | `docs/ideation.md` | ✅ Ready | — |
| 9 | LLD document | Components, data model, interfaces | `docs/lld.md` | ✅ Ready | — |
| 10 | Runbook | Operate, monitor and recover | `docs/runbook.md` (backfill + rollback + failure-alert drills done) | ✅ Ready | — |

**Score: 8 ready · 1 partial (UI wireframes) · 1 pending (presentation).**

## Presentation topics
| Topic | Material we have | Status |
|---|---|---|
| Business alignment | `docs/requirements.md` (FR/NFR, KPIs), `docs/ideation.md` (problem, goals → KPIs), RTM | ✅ Material ready, slides pending |
| IT security guidelines | `.env` git-ignored with random secrets (`init_env.sh`); read-only `bi_reader` for Superset (drill: refused `create table`); ports bound to 127.0.0.1; no PII (meter IDs only); pinned images; secrets never printed (`demo.sh`) | ✅ Material ready, slides pending |
| Performance testing | 7-day runs: backfill 174–225 s, demo 658 s (SLA ≤ 15 min per day of data) | ❌ 10× (70-day) test pending |

## Extra artifacts (count towards the demo and artifacts score)
| Artifact | File |
|---|---|
| Requirements + RTM | `docs/requirements.md`, `docs/rtm.md` |
| Architecture + 6 ADRs | `docs/architecture.md`, `docs/adr/ADR-001…006` |
| Data dictionary (generated) | `docs/data_dictionary.md` |
| Setup guide (Linux + Windows) | `docs/setup.md` |
| Scrum set | DoR, DoD, RAID, velocity, `sprint_0…3.md` |
| Completion report | `docs/completion_report.md` |
| Progress log | `docs/PROGRESS.md` |
| Evidence | `docs/evidence/sprint_0…3/` |

## Open items
1. **Failure e-mails:** decision 27-Nov-2026 (Sagar Kalthiya) is to keep e-mail disabled (assumption A9). Failures alert through `ops.alerts` (CRITICAL `task_failed`), the dashboard's Pipeline health tab and the Airflow logs. The SMTP path is coded and unit-tested; to enable it, set `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` in `.env` and run `docker compose up -d`.
2. **CI/CD on GitHub:** run `gh auth refresh -h github.com -s workflow`, then push `ci.yml` and `cd.yml`.
3. Performance test at 10×.
4. UI designs: wireframe + screenshots.
5. Presentation deck + 5-minute demo script.
