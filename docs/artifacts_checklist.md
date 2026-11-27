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
| 5 | UI designs | Wireframes and final screens | Dashboard as code: `scripts/superset_dashboard.py` (4 tabs, 9 charts) | ❌ Pending | Wireframe of the 4 tabs + screenshots of the live dashboard (http://localhost:8088/superset/dashboard/gridpulse/) saved under `docs/ui/` |
| 6 | Stories (Excel) | Backlog with acceptance criteria | `docs/scrum/product_backlog.xlsx` (+ `.md`) | ✅ Ready | 23 stories / 111 pts; 96 accepted |
| 7 | Application demo | Running app, five-minute walkthrough | Stack running locally (Airflow :8080, Superset :8088) | 🟡 Partial | App is running. Write the 5-minute demo script and rehearse it. |
| 8 | Ideation document | Problem, options, chosen approach | `docs/ideation.md` | ✅ Ready | — |
| 9 | LLD document | Components, data model, interfaces | `docs/lld.md` | ✅ Ready | — |
| 10 | Runbook | Operate, monitor and recover | `docs/runbook.md` (backfill + rollback + failure-alert drills done) | ✅ Ready | — |

**Score: 7 ready · 1 partial · 2 pending.**

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
1. **Failure e-mails:** code is ready and tested; needs SMTP settings in `.env` (see the question to the team).
2. **CI/CD on GitHub:** run `gh auth refresh -h github.com -s workflow`, then push `ci.yml` and `cd.yml`.
3. Performance test at 10×.
4. UI designs: wireframe + screenshots.
5. Presentation deck + 5-minute demo script.
