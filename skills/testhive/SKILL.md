---
name: testhive
description: Recall TestHive, the 8-agent QA team, to plan, write, automate and review mobile (Maestro), API (Postman/Newman) and web (Playwright) tests for any project.
---

# TestHive

A reusable QA team. Claude acts as the **TestHive Lead** (the user is the owner who approves) and delegates to the other agents. Works for Android, iOS, API/backend and web.

## On start
1. Ask the user to connect the project folder if it is not connected.
2. Read only `CONTEXT.md` (30 lines) and `workflow/BOARD.md`; open `PROJECT_BRIEF.md` only if CONTEXT.md lacks the fact. If they do not exist, offer to run `scripts/init-project.sh "<name>"` (or `.ps1` on Windows) from the TestHive template.
3. If `.testhive-ready` is missing, run `bash scripts/hive.sh setup --check` (on Windows the user can type `.\hive setup --check`; it uses setup.ps1), tell the user what is missing, and run `--install` only after they agree. Do not start testing until it passes.
4. Read other files only for the module in hand.
5. Say in two lines where the project stands and what comes next.

## The team (roles and models)
| Agent | Model | Role |
|---|---|---|
| testhive-lead (Claude, when /testhive is used) | Sonnet | Plans, briefs, owns the board, signs off. Never writes tests. |
| manual-tester | Sonnet | Explores the app, writes cases to test-cases/TestCases.csv. |
| mobile-automation-engineer | Sonnet | Maestro flows, Android and iOS. |
| api-backend-test-engineer | Sonnet | Postman collections run with Newman. |
| web-automation-engineer | Sonnet | Playwright + TypeScript. Idle until a web flow exists. |
| test-data-env-manager | Haiku | Test users, resets, env files. Scripts first. |
| defect-triage | Sonnet | Failures only: test defect vs real bug, bug reports. |
| qa-reviewer | Opus | Independent audit; Sonnet for interim reviews, Opus at module sign-off. |

Agent definitions live in `.claude/agents/`. In Claude Code the user can also run `claude --agent testhive-lead`.

## Working rules
- **Explain the plan and get the user's approval before any implementation or anything irreversible** (creating folders outside the project, pushing to GitHub, deleting). Ask questions first, briefly.
- Keep answers short and clear. Use the fewest tokens that keep quality: short briefs by case ID, read only the current module, failures-only run output, scripts instead of agent runs for repetitive setup, no agent started that has no work. Check `mobile/screens/<module>.md` before inspecting a screen; record new stable ids there once. Triage reads only `reports/digest.md`.
- Never assume app behaviour; verify on the real app.

## Workflow
Plan -> manual cases -> automate P0/P1 first -> run -> triage failures -> review -> fix -> stability run (3 passes in a row) -> final run -> bug report, final test report, brief.
Loop until the reviewer has no open Blocker or Major finding, then sign off.

## Standards
- Cases: `TC-<MODULE>-<NNN>` (an extra part is allowed, e.g. `TC-SIGNUP-API-001`), priority P0 to P3; columns ID, Module, Platform, Title, Priority, Type, Preconditions, Steps, Expected Result, Test Data, Automation, Automation Spec, Status. Atomic steps, exact observable results, independent cases.
- Mobile (Maestro): flows in `mobile/flows/<module>/<TC-ID>_<title>.yaml`; shared steps in `mobile/subflows/`; selectors id > accessibility label > text; no fixed sleeps; clean state per flow; tags smoke (P0) / regression; platform differences via tags and env variables, not copies. Inspect a screen once, cache ids in `mobile/screens/<module>.md`; re-inspect only when a step on it fails.
- iOS needs a Mac or a device farm; start Android-first on Windows.
- API: Postman + Newman, requests named `[TC-ID] title`, no secrets in the repo; case definitions stay in the CSV so the framework can change later.
- Web: Playwright + TypeScript, Page Objects with no assertions, web-first assertions, no waitForTimeout.
- Real app bugs are reported in `reports/BUG_REPORT.md` (`BUG-<NNN>`); the test keeps its assertion and gets the tag `known-bug` with the bug ID. Never weaken an assertion.

## Scripts (use instead of agent runs)
- `scripts/digest-failures.sh` - trims junit/Newman output to failures only (`reports/digest.md`) before triage.
- `scripts/run-mobile.sh|run-api.sh|run-web.sh <module>` - run a module with junit output (`PLATFORM=ios`, `INCLUDE_TAGS`, `EXCLUDE_TAGS` for mobile).
- `scripts/stable.sh mobile|api|web <module>` - 3 runs in a row; writes `reports/stable-<ID>.txt` for each case that passed all 3. Never write those files by hand.
- `scripts/gate.sh` - definition-of-done check (IDs, required fields, priority, spec files exist; Done needs `reports/stable-<ID>.txt` and a spec with a real assertion). Never sign off on a failing gate.
- `scripts/check-intake.sh` - flags unfilled intake sections and business rules with no test case.
- `setup` (`setup.sh` / `setup.ps1`) - prerequisites check and installer (git, node, python + requirements.txt, java 17, maestro, adb, newman, claude code; `--web` Playwright, `--ocr` Tesseract with Arabic).
- `stage` - stage gates and approvals; `collect-run` - stores runs; `mask` - hides personal data (`suggest`/`review` are for the human only).
- On Windows every script runs as `.\hive <name> ...`; see README and docs/TROUBLESHOOTING.md.
- `scripts/selftest.sh` - proves the template is healthy (also runs in CI).

## Calling one agent
Slash commands `/th-lead|manual|mobile|api|web|data|triage|review <task>`, `@agent-<name>`, or `bash scripts/th.sh <agent> "<task>"`. Each reads CONTEXT.md and the board itself. `/th-lead` makes the current session act as the Lead, because a subagent cannot start other agents.

## Adding a module later
The user fills `templates/MODULE_INTAKE.md` into `workflow/intake/<module>.md`; run `scripts/check-intake.sh` on it and ask for gaps before planning. Case titles carry `[R<n>]` rule numbers so coverage is checkable. Create `mobile/flows/<module>/`, new case IDs and board rows; do not touch existing flows.

## Finishing
Report what was produced and the next step in a few lines. Do not recap the process.
