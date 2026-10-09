# TestHive

A reusable team of AI QA agents for Claude. It plans, writes, automates and reviews tests for **mobile (Android + iOS, Maestro)**, **API/backend (Postman + Newman)** and **web (Playwright)**, and it scales one module at a time.

![How TestHive works](docs/testhive-diagram.png)

## The team (8 agents)

| Agent | Model | Role |
|---|---|---|
| `testhive-lead` | Sonnet | Plans, briefs, owns the board, signs off. Never writes tests. |
| `manual-tester` | Sonnet | Explores the app, writes test cases with exact expected results. |
| `mobile-automation-engineer` | Sonnet | Maestro flows for Android and iOS. |
| `api-backend-test-engineer` | Sonnet | Postman collections run with Newman. |
| `web-automation-engineer` | Sonnet | Playwright + TypeScript. Idle until a web flow exists. |
| `test-data-env-manager` | Haiku | Test users, resets, environment files. Scripts first. |
| `defect-triage` | Sonnet | Runs on failures only: test defect or real bug, writes bug reports. |
| `qa-reviewer` | Opus | Independent audit and module sign-off. |

## How it works
Plan -> cases -> automate P0/P1 first -> run -> triage failures -> review -> fix -> stability run (3 passes in a row) -> reports.

## Token-saving design
- Idle agents (web) are not started until needed.
- Repetitive setup is done by scripts in `scripts/`, not by agents.
- Defect Triage runs only on failures.
- Interim reviews use Sonnet; Opus is used for module sign-off.
- Each agent has only the tools it needs; runs print failures only; screen hierarchy is read only when a step fails.
- `CONTEXT.md` (30 lines) is read by agents instead of the full brief.
- Mobile screen ids are cached once in `mobile/screens/` and reused.
- `scripts/digest-failures.sh` trims run output to failures only before triage.
- `scripts/gate.sh` is a hard definition-of-done check; `scripts/selftest.sh` (also run in CI) proves the template works.
- Short briefs by case ID, one CSV for all cases, shared subflows and data.

## Requirements
- [Claude Code](https://claude.com/claude-code) (or Claude desktop app with the project folder connected)
- [Maestro CLI](https://maestro.mobile.dev), Android platform-tools (`adb`)
- Node.js and `npm i -g newman` for API runs
- iOS: a Mac (or cloud Mac / device farm). Windows cannot run the iOS Simulator.

## Quick start
See [QUICKSTART.md](QUICKSTART.md).

## Layout
```
skills/testhive/  the /testhive recall skill (copy to your Claude skills to use it)
.claude/agents/   the 8 agent definitions
templates/        project brief, CONTEXT, board, test case sheet, env example
mobile/           Maestro flows, subflows, data, android/ios notes
api/              Postman collections and environments
web/              Playwright (when needed)
scripts/          init, device check, reset, run, digest-failures, gate, selftest
workflow/         BOARD.md (created by init)
test-cases/       TestCases.csv and exploration notes (created by init)
reviews/ reports/ review files and run output
```

## Rules the team follows
- Verify against the real app; never assume behaviour.
- Cases: `TC-<MODULE>-<NNN>`, atomic steps, exact expected results, independent.
- Mobile selectors: id, then accessibility label, then text. No fixed sleeps.
- Real bugs are reported and the test keeps its assertion. Assertions are never weakened.
- A test is done only when it passes 3 times in a row.

## License
MIT. See [LICENSE](LICENSE).
