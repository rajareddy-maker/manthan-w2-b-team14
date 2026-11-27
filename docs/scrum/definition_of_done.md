# Definition of Done

A story is Done only when all of these are true:

- [ ] All acceptance criteria demonstrated with real command output
- [ ] Code on a feature branch (`feature/US-xx-…`), merged to main via a reviewed PR (squash)
- [ ] Linting passes (ruff, black, sqlfluff); CI pipeline green
- [ ] Unit tests added/updated and passing; dbt tests passing
- [ ] Great Expectations checkpoint passing for affected layers
- [ ] No secrets in code; config via environment variables
- [ ] Defects found are logged in docs/test_results.md; evidence saved in docs/evidence/
- [ ] `make demo` still runs end to end on a fresh clone
- [ ] Docs updated (README, LLD, data dictionary, runbook as relevant)
- [ ] RTM updated: requirement → code → test
- [ ] Story status set to Done on the sprint board and backlog (.md and .xlsx)
